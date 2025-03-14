# # api/schemas.py

# from drf_spectacular.utils import OpenApiParameter, OpenApiExample
# from drf_spectacular.types import OpenApiTypes

# # Schema definition for file upload
# file_upload_schema = {
#     'multipart/form-data': OpenApiParameter(
#         name='files',
#         description='Upload multiple PDF files',
#         required=True,
#         style='form',
#         explode=True,
#         examples=[
#             OpenApiExample(
#                 'Example 1',
#                 summary='Single PDF File',
#                 value='file_example.pdf',
#                 media_type='application/pdf'
#             ),
#             OpenApiExample(
#                 'Example 2',
#                 summary='Multiple PDF Files',
#                 value=['file1_example.pdf', 'file2_example.pdf'],
#                 media_type='application/pdf'
#             )
#         ]
#     )
# }
