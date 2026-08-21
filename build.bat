# 进入项目目录
cd E:\156soft\156 Markdown Editor

# 确认 bin 文件夹存在，包含 wkhtmltopdf.exe 和 pandoc.exe

# 打包
pyinstaller --onefile --windowed --uac-admin --add-data "bin;bin" --hidden-import pypandoc --hidden-import markdown.extensions.extra --hidden-import markdown.extensions.toc --collect-all customtkinter --collect-all pywinstyles --icon=icon.ico main.py