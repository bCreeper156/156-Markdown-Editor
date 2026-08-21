# 156 Markdown Editor

[中文简体](README.md) · [English](README_EN.md)

> 一款追求 Win11 原生体验的轻量 Markdown 编辑器

## 功能

- 实时大纲导航
- 文件新建/打开/保存/另存为
- 浅色/深色主题切换
- 静默保存（Ctrl+S）


## 特点
一个拒绝 Chromium、使用Tk制作UI的 25.4MB 原生级 WYSIWYG 编辑器。
采用正则表达式和mistune混合渲染模式，让程序更稳定！
我们专为Windows x64制作该软件，其他平台需要安装对应依赖并构建才可使用！

## 从源码构建

### 1.安装Python

请进入[Python官网](https://python.org)下载Python3.11.3并在安装时勾选添加至环境变量。

### 2.安装pip依赖

```bash
pip install -r requirements.txt
```
### 3.安装其他依赖

创建bin 文件夹存在，放入 wkhtmltopdf.exe 和 pandoc.exe。

### 4.使用构建脚本

双击build.bat（Windows用户使用）/build.sh（暂未编写，Linux和mac OS用户使用）
