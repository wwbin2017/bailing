"""Exercise the production loader, dispatcher, MCP wire and result consumer."""
import asyncio
import json
import os
import queue
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx

from bailing.dialogue import Dialogue
from plugins import parallel_mcp
from plugins.registry import Action
# The unrelated scheduler starts a perpetual thread at import time. Keep the
# real plugin loader, but suppress background thread startup during this import.
with patch("threading.Thread.start"):
    from plugins.task_manager import TaskManager

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {"functions_call_name": str(ROOT / "plugins/function_calls_config.json")}
REAL_CLIENT = httpx.AsyncClient


class MCPServer:
    def __init__(self, failure=None, sse=False):
        self.requests = []
        self.failure = failure
        self.sse = sse
        self.closed = []

    def client(self, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(self.handle), **kwargs)

    def handle(self, request):
        payload = json.loads(request.content)
        self.requests.append((request, payload))
        method = payload['method']
        if method == 'initialize':
            result = {"protocolVersion": parallel_mcp.PROTOCOL_VERSION}
        elif method == 'notifications/initialized':
            return httpx.Response(202)
        elif method == 'tools/list':
            result = {"tools": [{"name": "web_search"}, {"name": "web_fetch"}]}
        else:
            if self.failure == 'timeout':
                raise httpx.ReadTimeout('slow response', request=request)
            if self.failure == 'http':
                return httpx.Response(503)
            if self.failure == 'quota':
                result = {"isError": True, "content": [{"type": "text", "text": "free anonymous quota exceeded"}]}
            elif self.failure == 'rpc':
                return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload['id'], "error": {"code": -32603}})
            elif self.failure == 'malformed':
                return httpx.Response(200, content='not json')
            else:
                result = {"content": [{"type": "text", "text": json.dumps({"results": [{
                    "title": "Python", "url": "https://www.python.org/", "excerpts": ["Python documentation"]}]})}]}
        reply = {"jsonrpc": "2.0", "id": payload['id'], "result": result}
        headers = {"mcp-session-id": "connection-id"}
        if self.sse:
            # Ignore notifications and join multiline SSE data correctly.
            body = 'event: message\ndata: {"jsonrpc":"2.0","method":"ping"}\n\n'
            body += 'event: message\ndata: ' + json.dumps(reply, indent=2).replace('\n', '\ndata: ') + '\n\n'
            return httpx.Response(200, text=body, headers=dict(headers, **{"content-type": "text/event-stream"}))
        return httpx.Response(200, json=reply, headers=headers)

    def calls(self):
        return [p['params'] for _, p in self.requests if p['method'] == 'tools/call']


class ParallelRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.managers = []

    def tearDown(self):
        for manager in self.managers:
            manager.task_executor.shutdown(wait=True)

    def manager(self, config=None, dialogue=None):
        manager = TaskManager(config or CONFIG, queue.Queue(),
                              search_session_id=dialogue.search_session_id if dialogue else None)
        self.managers.append(manager)
        return manager

    def invoke(self, manager, query='Python language documentation'):
        return manager.tool_call('parallel_web_search', json.dumps({"query": query}))

    def test_shipped_loader_dispatch_and_anonymous_wire(self):
        manager = self.manager()
        names = [x['function']['name'] for x in manager.get_functions()]
        self.assertIn('parallel_web_search', names)
        self.assertIn('parallel_web_fetch', names)
        server = MCPServer()
        with patch.dict(os.environ, {"PARALLEL_API_KEY": "unused-ambient-key", "OPENAI_API_KEY": "unused"}), \
                patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
            result = self.invoke(manager)
        self.assertEqual(result.action, Action.REQLLM)
        self.assertIn('https://www.python.org/', result.result)
        self.assertEqual([p['method'] for _, p in server.requests],
                         ['initialize', 'notifications/initialized', 'tools/list', 'tools/call'])
        for request, payload in server.requests:
            self.assertEqual(str(request.url), 'https://search.parallel.ai/mcp')
            self.assertEqual(request.headers['user-agent'], parallel_mcp.USER_AGENT)
            self.assertNotIn('authorization', request.headers)
            if payload['method'] != 'initialize':
                self.assertEqual(request.headers['mcp-session-id'], 'connection-id')
                self.assertEqual(request.headers['mcp-protocol-version'], parallel_mcp.PROTOCOL_VERSION)
        self.assertEqual(server.calls()[0]['arguments']['session_id'], manager.search_session_id)

    def test_conversation_lifetime_interleaving_retry_and_new_chat(self):
        one = self.manager(dialogue=Dialogue('/unused'))
        two = self.manager(dialogue=Dialogue('/unused'))
        server = MCPServer()
        with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
            self.invoke(one)
            one.tool_call('parallel_web_fetch', {"urls": ["https://www.python.org/"]})
            self.invoke(two)
            server.failure = 'quota'
            self.invoke(one)
            server.failure = None
            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(self.invoke, [one, two]))
            # Bailing creates a new Dialogue and TaskManager for a new Robot.
            new_chat = self.manager(dialogue=Dialogue('/unused'))
            self.invoke(new_chat)
        ids = [c['arguments']['session_id'] for c in server.calls()]
        self.assertEqual(ids[:4], [one.search_session_id, one.search_session_id,
                                   two.search_session_id, one.search_session_id])
        self.assertCountEqual(ids[4:6], [one.search_session_id, two.search_session_id])
        self.assertEqual(ids[6], new_chat.search_session_id)
        self.assertEqual(len({one.search_session_id, two.search_session_id, new_chat.search_session_id}), 3)

    def test_custom_disabled_tools_and_context_override(self):
        with tempfile.TemporaryDirectory() as directory:
            custom = Path(directory) / 'tools.json'
            # Saved explicit legacy provider remains the only advertised tool.
            saved = [{"type": "function", "function": {"name": "web_search", "parameters": {}}}]
            custom.write_text(json.dumps(saved))
            manager = self.manager({"functions_call_name": str(custom)})
            self.assertEqual(manager.get_functions(), saved)
            self.assertEqual(self.invoke(manager).action, Action.NOTFOUND)
        enabled = self.manager()
        server = MCPServer()
        with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
            enabled.tool_call('parallel_web_search', {"query": "Python", "_session_id": "model-cannot-replace"})
        self.assertEqual(server.calls()[0]['arguments']['session_id'], enabled.search_session_id)

    def test_invalid_arguments_make_no_requests(self):
        manager = self.manager()
        server = MCPServer()
        with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
            for urls in [[], ['file:///etc/passwd'], ['https://user:secret@example.com'],
                         ['https:///bad'], ['https://[invalid'], ['https://example.org'] * 21]:
                self.assertEqual(manager.tool_call('parallel_web_fetch', {"urls": urls}).action, Action.REQLLM)
            self.invoke(manager, ' ')
            manager.tool_call('parallel_web_search', '[]')
        self.assertFalse(server.requests)

    def test_missing_and_unexpected_arguments_return_tool_errors(self):
        manager = self.manager()
        server = MCPServer()
        with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
            for name, arguments in [
                    ('parallel_web_search', {}), ('parallel_web_fetch', {}),
                    ('parallel_web_search', {"query": "Python", "unexpected": "x"}),
                    ('parallel_web_fetch', {"urls": ["https://www.python.org/"], "unexpected": "x"}),
                    ('parallel_web_search', {"urls": ["https://www.python.org/"]}),
                    ('parallel_web_fetch', {"query": "Python"})]:
                with self.subTest(name=name, arguments=arguments):
                    result = manager.tool_call(name, json.dumps(arguments))
                    self.assertEqual(result.action, Action.REQLLM)
                    self.assertIsInstance(result.result, str)
                    self.assertTrue(result.result)
        self.assertFalse(server.requests)

    def test_protocol_errors_timeouts_and_sse(self):
        manager = self.manager()
        for failure in ['timeout', 'http', 'quota', 'rpc', 'malformed']:
            with self.subTest(failure=failure):
                server = MCPServer(failure=failure)
                with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
                    result = self.invoke(manager)
                self.assertEqual(result.action, Action.REQLLM)
                self.assertNotIn('https://www.python.org/', result.result)
                self.assertTrue(result.result)
                self.assertEqual(len(server.calls()), 1)  # no provider fallback or automatic retry
        server = MCPServer(sse=True)
        with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
            self.assertIn('https://www.python.org/', self.invoke(manager).result)

    def test_total_deadline_and_cancellation_close_transport(self):
        class HangingTransport(httpx.AsyncBaseTransport):
            def __init__(self):
                self.closed = False
            async def handle_async_request(self, request):
                await asyncio.Event().wait()
            async def aclose(self):
                self.closed = True
        async def exercise(cancel):
            transport = HangingTransport()
            def client(**kwargs):
                return REAL_CLIENT(transport=transport, **kwargs)
            with patch.object(parallel_mcp.httpx, 'AsyncClient', client), patch.object(parallel_mcp, 'TIMEOUT', 0.02):
                task = asyncio.create_task(parallel_mcp.call_tool('web_search', {"session_id": 'test-conversation'}))
                if cancel:
                    await asyncio.sleep(0)
                    await asyncio.sleep(0)
                    task.cancel()
                with self.assertRaises(asyncio.CancelledError if cancel else asyncio.TimeoutError):
                    await task
            self.assertTrue(transport.closed)
        asyncio.run(exercise(False))
        asyncio.run(exercise(True))

    def test_scripted_robot_loop_consumes_search_results(self):
        # Hardware boundaries are stubbed; the Robot tool loop, TaskManager,
        # Dialogue and HTTP MCP client below are production code.
        audio_modules = {"bailing." + name: ModuleType("bailing." + name)
                         for name in ['recorder', 'player', 'asr', 'tts', 'vad', 'memory']}
        with patch.dict('sys.modules', audio_modules):
            from bailing.robot import Robot
        robot = Robot.__new__(Robot)
        robot.dialogue = Dialogue('/unused')
        robot.task_manager = self.manager(dialogue=robot.dialogue)
        robot.tts_queue = queue.Queue()
        spoken = []
        robot.speak_and_play = lambda text: spoken.append(text)
        robot.executor = ThreadPoolExecutor(max_workers=1)
        observed = []
        class ScriptedLLM:
            def response_call(self, dialogue, functions_call):
                observed.append(dialogue)
                if len(observed) == 1:
                    call = SimpleNamespace(id='search-1', function=SimpleNamespace(
                        name='parallel_web_search', arguments='{"query":"Python language documentation"}'))
                    yield None, [call]
                else:
                    self_outer.assertIn('https://www.python.org/', dialogue[-1]['content'])
                    yield 'Python documentation: https://www.python.org/.', None
        self_outer = self
        robot.llm = ScriptedLLM()
        server = MCPServer()
        try:
            with patch.object(parallel_mcp.httpx, 'AsyncClient', server.client):
                robot.chat_tool('Find Python documentation')
        finally:
            robot.executor.shutdown(wait=True)
        self.assertEqual(len(observed), 2)
        self.assertEqual(observed[1][-1]['role'], 'tool')
        self.assertIn('https://www.python.org/', ''.join(spoken))
        self.assertEqual(server.calls()[0]['arguments']['session_id'], robot.dialogue.search_session_id)


if __name__ == '__main__':
    unittest.main()
