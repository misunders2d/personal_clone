# from google import genai
# from google.genai import types
# import time

# from .. import config

# # client = genai.Client(
# #     project = config.GOOGLE_CLOUD_PROJECT,
# #     location = config.GOOGLE_CLOUD_LOCATION,
# #     credentials = json.loads(config.GCP_SERVICE_ACCOUNT_INFO),
# #     vertexai=True
# #     )

# client = genai.Client(api_key=config.GEMINI_API_KEY, vertexai=False)


# def create_file_search_store(display_name: str):
#     # Create the file search store with an optional display name
#     file_search_store = client.file_search_stores.create(
#         config={"display_name": display_name}
#     )
#     return file_search_store


# def get_file_search_store(store_name: str):

#     file_search_store_list = client.file_search_stores.list()
#     for store in file_search_store_list:
#         if store.display_name == store_name:
#             return store
#     return None


# def upload_file_to_store(file_path: str, unique_file_name: str):
#     # Upload and import a file into the file search store, supply a unique file name which will be visible in citations
#     try:
#         file_search_store = get_file_search_store("rag_documents")
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
#     if not file_search_store:
#         return {
#             "status": "error",
#             "message": "File search store `rag_documents` not found.",
#         }
#     if file_search_store.name:
#         operation = client.file_search_stores.upload_to_file_search_store(
#             file=file_path,
#             file_search_store_name=file_search_store.name,
#             config={
#                 "display_name": unique_file_name,
#             },
#         )
#         # Wait until import is complete
#         while not operation.done:
#             time.sleep(5)
#             operation = client.operations.get(operation)
#         return {
#             "status": "success",
#             "message": f"File {unique_file_name} uploaded successfully.",
#         }
#     return {"status": "error", "message": "File search store name not found."}


# def search_file_store(query: str):
#     file_search_store = get_file_search_store("rag_documents")
#     if not file_search_store or not file_search_store.name:
#         return {
#             "status": "error",
#             "message": "File search store `rag_documents` not found.",
#         }
#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=query,
#         config=types.GenerateContentConfig(
#             tools=[
#                 types.Tool(
#                     file_search=types.FileSearch(
#                         file_search_store_names=[file_search_store.name]
#                     )
#                 )
#             ]
#         ),
#     )
#     return response.text
