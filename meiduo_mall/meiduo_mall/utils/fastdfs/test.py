from fdfs_client.client import Fdfs_client


# 创建fast客户 加载客户端配置文件
client = Fdfs_client('./client.conf')


# 上传
ret = client.upload_by_filename('/Users/yanghu/Desktop/01.jpeg')
print(ret)

"""
{
'Group name': 'group1', 
'Remote file_id': 'group1/M00/00/00/wKhn0lzH0w6AN8ZBAAC4j90Tziw25.jpeg', 
'Status': 'Upload successed.', 
'Local file name': '/Users/chao/Desktop/01.jpeg', 
'Uploaded size': '46.00KB', 
'Storage IP': '192.168.103.210'}
"""
