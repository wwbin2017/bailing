# from plugins.registry import register_function, ToolType
# from plugins.registry import ActionResponse, Action
# from bailing.rag import Rag
#
# @register_function('search_local_documents', action=ToolType.TIME_CONSUMING)
# def search_local_documents(keyword: str):
#     rsp = Rag().query(keyword)
#     return ActionResponse(Action.RESPONSE, None, rsp)

# if __name__ == "__main__":
#     rsp = search_local_documents("大模型")
#     print(rsp.response, rsp.action, rsp.result)