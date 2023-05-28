# coding=UTF-8
import sys
from pathlib import Path
import requests
import json
import webbrowser
from collections import Counter
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QPlainTextEdit, QMessageBox
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QStyleFactory
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import uic
from common import CommonFunction
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import slvdata_resource

VERSION = '1.3'        # 当前版本号
MAX_REQUEST_NUM = 100  # 一次最大提交数量，单位：行

# 关于窗体
class About(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    # 动态加载UI文件
    def init_ui(self):
        self.ui = uic.loadUi("./ui/slvdata_about.ui", self)
        # 显示版本号
        self.lbl_version.setText(VERSION)
        QApplication.setStyle(QStyleFactory.create('Fusion'))

# 设置窗体
class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    # 动态加载UI文件
    def init_ui(self):
        self.ui = uic.loadUi("./ui/slvdata_setting.ui", self)
        pushBtnOK = self.ui.pushBtnOK
        pushBtnCancel = self.ui.pushBtnCancel
        # 定义槽函数
        pushBtnCancel.clicked.connect(self.close_window)
        pushBtnOK.clicked.connect(self.save_settings)
        # 改变界面Style
        QApplication.setStyle(QStyleFactory.create('Fusion'))

        # 获取连接信息
        # home_path = os.getcwd()
        home_path = Path.cwd()
        settings_filename = 'settings.ini'
        # settings_file = os.path.join(home_path, settings_filename)
        settings_file = Path.joinpath(home_path, settings_filename)
        cm = CommonFunction()
        account_id, api_key = cm.get_account_id_key(settings_file)
        self.lineEdtAccountID.setText(account_id)
        self.lineEdtAPIKEY.setText(api_key)


    def save_settings(self):
        account_id = self.lineEdtAccountID.text()
        api_key = self.lineEdtAPIKEY.text()

        # 信息填写错误，提醒
        if account_id.strip() == '' or api_key.strip() == '':
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)  # QMessageBox.Information，QMessageBox.Warning，QMessageBox.Critical
            msgBox.setWindowTitle("Error")
            msgBox.setText("错误")
            msgBox.setInformativeText('ACCOUNT-ID及API-KEY不能为空')
            msgBox.setDetailedText('')
            msgBox.exec()
            return -1

        # home_path = sys.path[0]
        # home_path = os.getcwd()
        home_path = Path.cwd()
        settings_filename = 'settings.ini'
        # settings_file = os.path.join(home_path, settings_filename)
        settings_file = Path.joinpath(home_path, settings_filename)
        # print(settings_file)
        try:
            if Path.exists(settings_file):
                Path.unlink(settings_file)
            # if os.path.exists(settings_file):
            #     os.remove(settings_file)
            # 保存到INI文件
            f = open(settings_file, 'w')
            f.write('ACCOUNT-ID=' + account_id + '\n')
            f.write('API-KEY=' + api_key + '\n')
            f.close()

            # 信息提醒已保存
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)  # QMessageBox.Information，QMessageBox.Warning，QMessageBox.Critical
            msgBox.setWindowTitle("Information")
            msgBox.setText("成功")
            msgBox.setInformativeText('已成功保存')
            msgBox.setDetailedText('')
            msgBox.exec()
        except Exception as e:
            # 信息提醒保存失败
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)  # QMessageBox.Information，QMessageBox.Warning，QMessageBox.Critical
            msgBox.setWindowTitle("Error")
            msgBox.setText("错误")
            msgBox.setInformativeText('保存失败')
            msgBox.setDetailedText(str(e))
            msgBox.exec()
        # 关闭对话框
        self.close()

    def close_window(self):
        self.close()

# 算法介绍窗体
class IntroWindow(QDialog):
    def __init__(self, analysis_type='sentiment', parent=None):
        super().__init__(parent)
        self.analysis_type = analysis_type
        self.init_ui()

    # 动态加载UI文件
    def init_ui(self):
        self.ui = uic.loadUi("./ui/slvdata_intro.ui", self)
        pushBtnClose = self.ui.pushBtnClose
        stackedWidget = self.ui.stackedWidget

        # 定义槽函数
        pushBtnClose.clicked.connect(self.close_window)

        # 显示对应的算法介绍页面
        if self.analysis_type == 'sentiment':
            stackedWidget.setCurrentIndex(0)
            # self.ui.stackedWidget.setCurrentIndex(0)
        elif self.analysis_type == 'classify':
            stackedWidget.setCurrentIndex(1)
        elif self.analysis_type == 'keyword':
            stackedWidget.setCurrentIndex(2)
        elif self.analysis_type == 'piidetect':
            stackedWidget.setCurrentIndex(3)
        # print(stackedWidget.currentIndex)

        # 改变界面Style
        QApplication.setStyle(QStyleFactory.create('Fusion'))

    def close_window(self):
        self.close()

# 主窗体
class SlvAppWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_analysis_type = None  # 当前分析的类别
        self.return_pattern = None         # 选择的返回样式
        self.account_id = None             # ACCOUNT-ID
        self.api_key = None                # API-KEY
        self.home_path = None          # APP HOME-PATH
        self.settings_filename = None  # Settings filename
        self.settings_file = None      # Settings file
        self.init_ui()

    def init_ui(self):
        # 动态加载UI文件
        self.ui = uic.loadUi("./ui/slvdata_main.ui", self)
        pushBtnIntro = self.ui.pushBtnIntro               # 介绍按钮
        toolBtnLoadData = self.ui.toolBtnLoadData         # 从文件加载数据按钮
        pushBtnClean = self.ui.pushBtnClean               # 清除按钮
        checkBoxWordwrap = self.ui.checkBoxWordwrap       # 自动换行
        pushBtnSubmit = self.ui.pushBtnSubmit             # 提交按钮
        pushBtnExport = self.ui.pushBtnExport             # 导出数据按钮
        pushBtnReport = self.ui.pushBtnReport             # 查看报表按钮
        action_set_connect = self.ui.action_set_connect   # 菜单 - 设置
        action_version = self.ui.action_version           # 菜单 - 关于
        action_exit = self.ui.action_exit                 # 菜单 - 退出
        action_sentiment = self.ui.action_sentiment       # 菜单 - 情感分析
        action_classify = self.ui.action_classify         # 菜单 - 评论分类
        action_keyword = self.ui.action_keyword           # 菜单 - 取关键词
        action_pii = self.ui.action_pii                   # 菜单 - PII检测
        action_help = self.ui.action_help                 # 菜单 - Help

        # 定义槽函数
        toolBtnLoadData.clicked.connect(self.load_data)
        pushBtnSubmit.clicked.connect(self.submit_data)
        pushBtnIntro.clicked.connect(self.show_intro_window)
        action_set_connect.triggered.connect(self.show_settings_window)
        action_version.triggered.connect(self.show_about)
        action_exit.triggered.connect(self.close_app)
        action_sentiment.triggered.connect(self.action_sentiment_func)
        action_classify.triggered.connect(self.action_classify_func)
        action_keyword.triggered.connect(self.action_keyword_func)
        action_pii.triggered.connect(self.action_pii_func)
        action_help.triggered.connect(self.action_help_func)
        pushBtnClean.clicked.connect(self.clear_text_input)
        checkBoxWordwrap.clicked.connect(self.plain_text_wordwrap)
        pushBtnExport.clicked.connect(self.export_data)
        pushBtnReport.clicked.connect(self.generate_report)

        # 启动时隐藏进度条
        self.progressBar.setVisible(False)
        # 清除输入及输出框
        self.clear_text_input()
        # 启动时默认转到情感分析
        self.action_sentiment_func()
        # 改变界面Style
        QApplication.setStyle(QStyleFactory.create('Fusion'))

        # 设置文件路径
        # self.home_path = sys.path[0]
        # self.home_path = os.getcwd()
        self.home_path = Path.cwd()
        self.settings_filename = 'settings.ini'
        # self.settings_file = os.path.join(self.home_path, self.settings_filename)
        self.settings_file = Path.joinpath(self.home_path, self.settings_filename)

        # 初始化时取ACCOUNT-ID及API-KEY，
        cm = CommonFunction()
        account_id, api_key = cm.get_account_id_key(self.settings_file)
        self.account_id = account_id
        self.api_key = api_key

    # 检测ACCOUNT-ID 以及 API-KEY
    def check_account_id_key(self):
        if not self.account_id or not self.api_key:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)  # QMessageBox.Information，QMessageBox.Warning，QMessageBox.Critical
            msgBox.setWindowTitle("Information")
            msgBox.setText("连接设置")
            msgBox.setInformativeText('连接设置信息不正确，请在菜单栏"设置"下的"连接设置"完成对应设置')
            msgBox.setDetailedText('')
            msgBox.exec()
            # 写状态栏
            self.statusbar.showMessage('连接设置信息不正确')
            return False
        else:
            return True

    # 加载数据文件
    def load_data(self):
        """选择文件对话框"""
        # QFileDialog组件定义
        fileDialog = QFileDialog(self)
        # QFileDialog组件设置
        fileDialog.setWindowTitle("选择数据文件")  # 设置对话框标题
        fileDialog.setFileMode(QFileDialog.AnyFile)  # 设置能打开文件的格式
        # fileDialog.setDirectory(r'D:\')  # 设置默认打开路径
        fileDialog.setNameFilter("Text (*.txt *.csv)")  # 按文件名过滤
        file_path = fileDialog.exec()  # 窗口显示，返回文件路径
        if file_path and fileDialog.selectedFiles():
            filename = fileDialog.selectedFiles()[0]
            # 先清空输入框及输出框
            self.clear_text_input()
            try:
                # 读文件并加载到数据框
                f = open(filename, 'r', encoding='utf-8')
                i_line = 0
                for line in f.readlines():   # 调用readlines()一次读取所有内容并按行返回list
                    s_line = line.strip().replace('\n','').replace('\r','')
                    if s_line != '':
                        self.plainTextInput.appendPlainText(s_line)
                        i_line = i_line + 1  # 文本行数
                # 显示文本行数在右上角
                self.lblLineCount.setText(str(i_line))
                # 写状态栏
                self.statusbar.showMessage('数据加载成功')
            except Exception as e:
                msg = 'Exception: ' + str(e)
                self.statusbar.showMessage(msg)   # 显示在状态栏
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Critical)   # QMessageBox.Information
                msgBox.setWindowTitle("Error")
                msgBox.setText("数据加载异常")
                msgBox.setInformativeText("加载数据文件\n" + filename + "\n出现异常")
                msgBox.setDetailedText(str(e))
                msgBox.exec()
            finally:
                if f:
                    f.close()

    # 导出分析结果的数据
    def export_data(self):
        text = self.plainTextOutput.toPlainText()
        if text.strip() == '':
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)  # QMessageBox.Information
            msgBox.setWindowTitle("Warning")
            msgBox.setText("数据为空")
            msgBox.setInformativeText("未发现需要保存的数据")
            # msgBox.setDetailedText("")
            msgBox.exec()
        else:
            filepath = QFileDialog.getSaveFileName(self, "保存数据到文件", '/', 'Text (*.txt)')[0]
            file = open(filepath, 'w', encoding='utf-8')
            file.write(text)
            file.close()

    # 生成报表
    def generate_report(self):
        text = self.plainTextOutput.toPlainText()
        if text.strip() == '':
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)  # QMessageBox.Information
            msgBox.setWindowTitle("Warning")
            msgBox.setText("数据为空")
            msgBox.setInformativeText("未发现用于生成报表的数据")
            # msgBox.setDetailedText("")
            msgBox.exec()
            return -1

        # 根据当前分析的类别及数据返回样式来整理准备用于生成报表的数据
        # 情感分析，只返回结果
        if self.current_analysis_type == 'sentiment':
            output_lst = []
            if self.return_pattern == 'P':  # 只返回结果，直接取得结果
                output_lst = text.split('\n')
            else:                           # 全量返回，先从末尾取结果
                output_lst_tmp = text.split('\n')
                for line in output_lst_tmp:
                    i_split = line.rfind('-')
                    output_lst.append(line[i_split + 1:].strip())

            # 得到画报表的数据
            counts = {}
            for item in output_lst:
                counts[item] = counts.get(item, 0) + 1
            types = list(counts.keys())
            counts = list(counts.values())

            # 画报表
            # ttf_file = os.path.join(self.home_path, 'SimHei.ttf')
            plt.rcParams['font.sans-serif'] = ['simhei']   # 设置字体 simhei
            fig = plt.figure()
            fig.canvas.manager.set_window_title('Report')  # 设置报表窗口标题
            plt.pie(counts, labels=types, autopct='%1.1f%%', startangle=90)
            plt.title('情感分析')  # 中文标题
            plt.show()
        # 评论分类，只返回结果
        elif self.current_analysis_type == 'classify':
            output_lst_tmp = []
            if self.return_pattern == 'P':  # 只返回结果，直接取得结果
                output_lst_tmp = text.split('\n')
            else:                           # 全量返回，先从末尾取结果
                output_lst_tmp_pre = text.split('\n')
                for line in output_lst_tmp_pre:
                    i_split = line.rfind('-')
                    output_lst_tmp.append(line[i_split + 1:].strip())
            # 整理数据，对于有“|”分割的，要再分解
            output_lst = []
            for tmp in output_lst_tmp:
                if tmp.find('|') < 0:
                    if tmp != 'NONE':
                        output_lst.append(tmp)
                else:
                    tmp_lst = tmp.split('|')
                    for item in tmp_lst:
                        if tmp != 'NONE':
                            output_lst.append(item)

            # 没数据立即退出
            if len(output_lst) <= 0:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)  # QMessageBox.Information
                msgBox.setWindowTitle("Information")
                msgBox.setText("无法生成报表")
                msgBox.setInformativeText("当前数据缺失，无法生成报表")
                # msgBox.setDetailedText()
                msgBox.exec()
                return -1

            # 统计不同类型的数量
            counts = Counter(output_lst)
            labels, values = zip(*counts.items())

            # 画报表
            plt.rcParams['font.sans-serif'] = ['simhei']  # 设置字体 simhei SimSun
            fig = plt.figure()
            fig.canvas.manager.set_window_title('Report')  # 设置报表窗口标题
            plt.bar(labels, values)
            plt.xlabel('类别')
            plt.ylabel('数量')
            plt.show()
        # 关键词
        elif self.current_analysis_type == 'keyword':
            output_lst_tmp = []
            if self.return_pattern == 'P':  # 只返回结果，直接取得结果
                output_lst_tmp = text.split('\n')
            else:  # 全量返回，先从末尾取结果
                output_lst_tmp_pre = text.split('\n')
                for line in output_lst_tmp_pre:
                    i_split = line.rfind('-')
                    output_lst_tmp.append(line[i_split + 1:].strip())
            # 整理数据，对于有“|”分割的，要再分解
            output_lst = []
            for tmp in output_lst_tmp:
                if tmp.find('|') < 0:
                    if tmp != 'NONE':
                        output_lst.append(tmp)
                else:
                    tmp_lst = tmp.split('|')
                    for item in tmp_lst:
                        if tmp != 'NONE':
                            output_lst.append(item)

            # 没数据立即退出
            if len(output_lst) <= 0:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)  # QMessageBox.Information
                msgBox.setWindowTitle("Information")
                msgBox.setText("无法生成报表")
                msgBox.setInformativeText("当前数据缺失，无法生成报表")
                # msgBox.setDetailedText()
                msgBox.exec()
                return -1

            # 统计每种类型的数量
            word_counts = {}
            for word in output_lst:
                if word in word_counts:
                    word_counts[word] += 1
                else:
                    word_counts[word] = 1

            # 创建词云对象
            wordcloud = WordCloud(width=800, height=400, stopwords='stopwords.txt', max_words=300, font_path='simhei.ttf', background_color='white')
            # 生成词云图像
            wordcloud.generate_from_frequencies(word_counts)

            # 绘制词云图像
            # plt.rcParams['font.sans-serif'] = ['SimSun']  # 设置字体
            # fig = plt.figure()
            # fig.canvas.manager.set_window_title('Report')  # 设置报表窗口标题
            plt.figure(figsize=(10, 6))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.show()
        # PII检测
        elif self.current_analysis_type == 'piidetect':
            if self.return_pattern in ['P', 'MP', 'MF']: #只要你不是P，即说明是返回脱敏的文本，无法生成报表
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)  # QMessageBox.Information
                msgBox.setWindowTitle("Information")
                msgBox.setText("无法生成报表")
                msgBox.setInformativeText("当前文本数据无法生成报表")
                # msgBox.setDetailedText()
                msgBox.exec()
            # 下面的代码目前无效，对PII这个不生成报表
            elif self.return_pattern == 'P': # 只返回结果
                row_values = []
                # 从结果框的text得到一个列表
                response_dic_lst = text.split('\n')
                for dic_str in response_dic_lst:
                    # 转换成字典
                    dic_str = dic_str.replace("'", "\"")
                    response_dic = json.loads(dic_str)
                    row_value = [response_dic['type'], response_dic['text']]
                    row_values.append(row_value)

                column_labels = ['PII_Type', 'PII_Text']
                # cellTexts = [soldNums]
                # rowLabels = ['价格']
                # 画报表
                plt.rcParams['font.sans-serif'] = ['simhei']  # 设置字体 simhei SimSun
                plt.table(cellText=row_values,  # 简单理解为表示表格里的数据
                          # colWidths=[0.3] * 4,  # 每个小格子的宽度 * 个数，要对应相应个数
                          colLabels=column_labels,  # 每列的名称
                          # colColours=colors,  # 每列名称颜色
                          # rowLabels=rowLabels,  # 每行的名称（从列名称的下一行开始）
                          rowLoc="center"  # 行名称的对齐方式
                          # loc="bottom"  # 表格所在位置
                          )
                plt.title("PII数据列表")
                plt.figure(dpi=80)
                plt.show()

    # 自动换行
    def plain_text_wordwrap(self):
        if self.checkBoxWordwrap.isChecked():
            self.plainTextInput.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            self.plainTextOutput.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.plainTextInput.setLineWrapMode(QPlainTextEdit.NoWrap)
            self.plainTextOutput.setLineWrapMode(QPlainTextEdit.NoWrap)

    # 转到情感分析
    def action_sentiment_func(self):
        self.current_analysis_type = 'sentiment'
        self.lblAnalysisType.setText('情感分析')
        self.plainTextInput.clear()
        self.plainTextOutput.clear()
        self.lblLineCount.setText('0')
        self.comboBoxReturnMode.setVisible(True)
        self.comboBoxReturnMode.setCurrentIndex(0)
        self.comboBoxReturnMode_PII.setVisible(False)
        self.groupBoxPII.setVisible(False)
        # 引用资源文件，引用.qrc资源中的文件时，路径为：冒号+prefix路径前缀+file相对路径
        map = QPixmap(":/type/image/sentiment_type.png")
        self.lblAnalysisTypeImg.setPixmap(map)

    # 转到评论分类
    def action_classify_func(self):
        self.current_analysis_type = 'classify'
        self.lblAnalysisType.setText('评论分类')
        self.plainTextInput.clear()
        self.plainTextOutput.clear()
        self.lblLineCount.setText('0')
        self.comboBoxReturnMode.setVisible(True)
        self.comboBoxReturnMode.setCurrentIndex(0)
        self.comboBoxReturnMode_PII.setVisible(False)
        self.groupBoxPII.setVisible(False)
        # 引用资源文件，引用.qrc资源中的文件时，路径为：冒号+prefix路径前缀+file相对路径
        map = QPixmap(":/type/image/classify_type.png")
        self.lblAnalysisTypeImg.setPixmap(map)

    # 转到取关键词
    def action_keyword_func(self):
        self.current_analysis_type = 'keyword'
        self.lblAnalysisType.setText('取关键词')
        self.plainTextInput.clear()
        self.plainTextOutput.clear()
        self.lblLineCount.setText('0')
        self.comboBoxReturnMode.setVisible(True)
        self.comboBoxReturnMode.setCurrentIndex(0)
        self.comboBoxReturnMode_PII.setVisible(False)
        self.groupBoxPII.setVisible(False)
        # 引用资源文件，引用.qrc资源中的文件时，路径为：冒号+prefix路径前缀+file相对路径
        map = QPixmap(":/type/image/keyword_type.png")
        self.lblAnalysisTypeImg.setPixmap(map)

    # 转到PII检测
    def action_pii_func(self):
        self.current_analysis_type = 'piidetect'
        self.lblAnalysisType.setText('PII检测')
        self.plainTextInput.clear()
        self.plainTextOutput.clear()
        self.lblLineCount.setText('0')
        self.comboBoxReturnMode.setVisible(False)
        self.comboBoxReturnMode_PII.setVisible(True)
        self.comboBoxReturnMode_PII.setCurrentIndex(0)
        self.groupBoxPII.setVisible(True)
        # 引用资源文件，引用.qrc资源中的文件时，路径为：冒号+prefix路径前缀+file相对路径
        map = QPixmap(":/type/image/pii_type.png")
        self.lblAnalysisTypeImg.setPixmap(map)

    # 打开帮助网页
    def action_help_func(self):
        webbrowser.open('http://slvdata.com/slvapp-help/')

    # 清空文本
    def clear_text_input(self):
        self.plainTextInput.clear()
        self.plainTextOutput.clear()
        self.lblLineCount.setText('0')

    # 显示关于窗体
    def show_about(self):
        about_window = About(self)
        about_window.setModal(True)
        about_window.exec_()

    # 显示算法介绍对话框
    def show_intro_window(self):
        intro_win = IntroWindow(analysis_type=self.current_analysis_type)
        intro_win.setModal(True)
        # intro_win.ui.show()
        intro_win.exec_()

    # 显示设置对话框
    def show_settings_window(self):
        settings_window = SettingsWindow(self)
        settings_window.setModal(True)
        settings_window.exec_()

    # 退出APP
    def close_app(self):
        self.close()

    # 提交数据
    def submit_data(self):
        self.setCursor(QCursor(Qt.BusyCursor))    # 设置鼠标为忙碌
        input_text = self.plainTextInput.toPlainText()
        input_text = input_text.strip()
        if input_text == '':
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)  # QMessageBox.Information，QMessageBox.Warning，QMessageBox.Critical
            msgBox.setWindowTitle("Information")
            msgBox.setText("数据为空")
            msgBox.setInformativeText('请输入或加载你需要分析的数据')
            msgBox.setDetailedText('')
            msgBox.exec()
            # 写状态栏
            self.statusbar.showMessage('数据为空')
            return False

        # 获取连接信息
        cm = CommonFunction()
        account_id, api_key = cm.get_account_id_key(self.settings_file)
        self.account_id = account_id
        self.api_key = api_key

        # 检查连接信息是否正确，不正确退出
        if not self.check_account_id_key():
            return False

        # 先清空返回结果框里的数据
        self.plainTextOutput.clear()

        # 准备API请求包头
        # # 包头的格式为如下
        # headers = {'content-type': 'application/json',
        #            'API-KEY': self.api_key,
        #            'ACCOUNT-ID': self.account_id,
        #            # 'INDUSTRY-TYPE': 'IND-000',      # 你公司行业类别
        #            'PROCESS-MODE': process_mode,
        #            'RETURN-PATTERN': return_pattern,
        #            'MASK-ITEMS': mask_items
        #            }
        headers = {'content-type': 'application/json'}
        # 加入当前版本号到包头，以备后续使用
        headers['version'] = VERSION
        # 分析类别
        if self.current_analysis_type == 'sentiment':
            process_mode = 'PRO-MD-100'
        elif self.current_analysis_type == 'classify':
            process_mode = 	'PRO-MD-101'
        elif self.current_analysis_type == 'keyword':
            process_mode = 'PRO-MD-102'
        elif self.current_analysis_type == 'piidetect':
            process_mode = 'PRO-MD-103'
        else:
            process_mode = 'PRO-MD-999'

        # 返回模式
        if self.current_analysis_type in ['sentiment','classify', 'keyword']:
            if self.comboBoxReturnMode.currentIndex() == 0:
                return_pattern = 'P'  # P: 只返回结果
            else:
                return_pattern = 'F'  # F: 全量返回
        elif self.current_analysis_type == 'piidetect':
            if self.comboBoxReturnMode_PII.currentIndex() == 0:
                return_pattern = 'P'   # P: 只返回PII位置信息
            elif self.comboBoxReturnMode_PII.currentIndex() == 1:
                return_pattern = 'MF'  # MF：返回脱敏后的文本(全替换方式，如手机号：***********)
            else:
                return_pattern = 'MP'  # MP：返回脱敏后的文本(部分替换方式，如手机号：1378*******)
            # PII检测，获取选中的PII项目
            mask_items = ""
            if self.checkBox_Phone.isChecked():
                mask_items = "'PHONE'"
            if self.checkBox_Email.isChecked():
                mask_items = mask_items + ",'EMAIL'"
            if self.checkBox_Person.isChecked():
                mask_items = mask_items + ",'PERSON'"
            if self.checkBox_ID.isChecked():
                mask_items = mask_items + ",'ID'"
            if self.checkBox_Location.isChecked():
                mask_items = mask_items + ",'LOCATION'"
            if self.checkBox_BankAccount.isChecked():
                mask_items = mask_items + ",'BANK_ACCOUNT'"
            if self.checkBox_IP.isChecked():
                mask_items = mask_items + ",'IP'"
            headers['MASK-ITEMS'] = mask_items
        else:
            return_pattern = 'P'
        self.return_pattern = return_pattern

        url = 'https://slvdata.com/api/'             # API请求的URL
        headers['API-KEY'] = self.api_key            # 你的API-KEY
        headers['ACCOUNT-ID'] = self.account_id      # 你的账号
        headers['PROCESS-MODE'] =  process_mode      # 数据处理方式
        headers['RETURN-PATTERN'] = return_pattern   # 数据返回的样式

        # 数据放进列表，准备提交数据
        input_lst = input_text.split("\n")
        # 显示文本行数在右上角
        self.lblLineCount.setText(str(len(input_lst)))

        try:
            self.progressBar.setVisible(True)       # 开始处理数据，显示进度条
            self.pushBtnSubmit.setEnabled(False)    # 禁用按钮，防止重复点击，工作线程结束后再启用
            self.toolBtnLoadData.setEnabled(False)  #
            self.pushBtnClean.setEnabled(False)     #
            self.pushBtnExport.setEnabled(False)    #
            self.pushBtnReport.setEnabled(False)    #
            self.checkBoxWordwrap.setEnabled(False) #
            self.plainTextInput.setEnabled(False)   #
            self.comboBoxReturnMode.setEnabled(False) #
            self.comboBoxReturnMode_PII.setEnabled(False) #
            self.groupBoxPII.setEnabled(False)      #
            self.toolBar.setEnabled(False)          # 工具栏 禁用
            self.menu_analysis.setEnabled(False)    # 分析菜单 禁用
            self.menu_setting.setEnabled(False)     # 设置菜单 禁用

            self.worker = PostDataThread(url, headers, input_lst, MAX_REQUEST_NUM)
            self.worker.progress_update.connect(self.update_progress)
            self.worker.result_received.connect(self.process_received_data)
            self.worker.finished.connect(self.data_submission_complete)
            self.worker.start()
            # 写状态栏
            self.statusbar.showMessage('处理中...')
        except Exception as e:
            print(str(e))


    def update_progress(self, progress_value):
        self.progressBar.setValue(progress_value)

    # 收到工作线程发回的处理结果
    def process_received_data(self, received_data):
        # 写状态栏
        self.statusbar.showMessage('收到返回的数据...')
        if received_data[0:5] == 'ERROR':
            self.plainTextOutput.appendPlainText('发生错误')
            self.plainTextOutput.appendPlainText('错误信息：' + received_data)
        elif received_data[0:9] == 'Exception':
            self.plainTextOutput.appendPlainText('发生异常')
            self.plainTextOutput.appendPlainText('异常信息：' + received_data)
        else:
            # 处理工作线程发回的数据，返回结果为JSON格式的的字符串，是字符串格式，可以转换成字典格式，
            response_dic = json.loads(received_data)
            # 这里response_dic=
            # {'message_code': 2000, 'data': {'1': '你好，请通过电话或邮件方式联系我，我的手机号码是1388*******，'}}
            return_code = response_dic['message_code']   # 返回码
            return_data = response_dic['data']           # 返回的数，字典格式
            # 成功返回
            if return_code == 2000:
                if self.current_analysis_type in ['sentiment', 'classify', 'keyword']:
                    # 遍历字典中的value追加到分析结果框
                    values = return_data.values()
                    for value in values:
                        self.plainTextOutput.appendPlainText(value)
                elif self.current_analysis_type == 'piidetect':
                    # 遍历字典中的value追加到分析结果框
                    values = return_data.values()
                    if self.return_pattern in ['MP', 'MF']:
                        for value in values:
                            self.plainTextOutput.appendPlainText(value)
                    else:
                        for value in values:
                            # 将单引号替换为双引号，用于后面转成字典列表
                            json_string = value.replace("'", "\"")

                            # 将末尾的",]"替换成“]”
                            if json_string[len(json_string)-2:] == ",]":
                                json_string = json_string.replace(",]", "]")

                            # 使用 json.loads() 将字符串转换为字典列表
                            dictionary_list = json.loads(json_string)

                            # 添加到结果框里
                            for lst in dictionary_list:
                                self.plainTextOutput.appendPlainText(str(lst))
                # 写状态栏
                self.statusbar.showMessage('本批次成功返回')
            else:
                self.plainTextOutput.appendPlainText('发生错误')
                self.plainTextOutput.appendPlainText('服务端返回码为：' + str(return_code))
                self.plainTextOutput.appendPlainText('返回信息：' + str(return_data))
                # 写状态栏
                self.statusbar.showMessage('返回码异常')

    # 工作线程处理结束，按钮等设为可用
    def data_submission_complete(self):
        self.setCursor(QCursor(Qt.ArrowCursor))  # 设置鼠标为普通箭头
        self.pushBtnSubmit.setEnabled(True)      # 启用按钮 - 提交
        self.toolBtnLoadData.setEnabled(True)    #
        self.pushBtnClean.setEnabled(True)       #
        self.pushBtnExport.setEnabled(True)      #
        self.pushBtnReport.setEnabled(True)      #
        self.checkBoxWordwrap.setEnabled(True)   #
        self.plainTextInput.setEnabled(True)  #
        self.comboBoxReturnMode.setEnabled(True)  #
        self.comboBoxReturnMode_PII.setEnabled(True)  #
        self.groupBoxPII.setEnabled(True)  #
        self.toolBar.setEnabled(True)            # 工具栏
        self.menu_analysis.setEnabled(True)      # 分析菜单 启用
        self.menu_setting.setEnabled(True)       # 设置菜单 启用
        self.progressBar.setValue(100)           # 完成后将进度条设置为100%
        self.progressBar.setVisible(False)       # 隐藏进度条

# 自定义的工作线程类，用于数据提交过程
#   post_url    - request url
#   headers     - request headers
#   input_lst   - request data (list of strings)
#   max_req_num - max number of requests every batch
class PostDataThread(QThread):
    progress_update = pyqtSignal(int)  # 定义一个信号，用于更新进度条的值
    result_received = pyqtSignal(str)  # 定义一个信号，用于传递接收到的数据

    def __init__(self, post_url, headers, input_lst, max_req_num):
        super().__init__()
        self.post_url = post_url
        self.headers = headers
        self.input_lst = input_lst
        self.max_req_num = max_req_num

    def run(self):
        # 发送请求到服务端
        def send_to_server(data):
            try:
                response = requests.post(self.post_url, data=json.dumps(data), headers=self.headers)
                if response.status_code == 200:
                    received_data = response.text
                    self.result_received.emit(received_data)  # 发送接收到的数据信号
                else:
                    received_data = 'ERROR, requests return code: ' + str(response.status_code)
                    self.result_received.emit(received_data)  # 发送接收到的数据信号
            except Exception as e:
                received_data = 'Exception: ' + str(e)
                self.result_received.emit(received_data)  # 发送接收到的数据信号
            data.clear()  # 清空字典

        total_count = len(self.input_lst)   # 总行数
        i_current = 0                       # 当前行数
        data = {}

        while True:
            if i_current > total_count-1:
                break
            # 列表里取到数据
            line = self.input_lst[i_current]
            i_current += 1
            # 发送进度信号
            self.progress_update.emit((i_current + 1) * 100 // total_count)

            if line.strip() != '':
                data[str(i_current)] = line.strip()

            # 每取 max_req_num 次提交一次到服务器
            if i_current % self.max_req_num == 0:
                # 判断字典data里是否有值，有才发送
                if bool(data):
                    # 发送请求到服务端
                    send_to_server(data)
        # 判断字典里还有值，再次提交，假如每批次提交100行，当总共有130行时，最后需要提交那30行
        if bool(data):
            send_to_server(data)


def main():
    app = QApplication(sys.argv)
    # 主窗体
    main_win = SlvAppWindow()
    # 显示主窗体
    main_win.ui.showMaximized()
    # main_win.ui.show()
    app.exec_()

if __name__ == "__main__":
    main()
