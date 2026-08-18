import os
import re
import sys
import argparse

import py7zr
import tempfile
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QKeySequence, QTextDocument
from PyQt5.QtWidgets import QTreeWidgetItem, QShortcut, QMessageBox, QStyledItemDelegate

import viewer
from ottosave.arc import loadObarc, loadObarcBytes
from ottosave import formatTime, Config, setGlobalConfig


def parse_args():
    parser = argparse.ArgumentParser(description="Ottoread args")
    parser.add_argument("--bid", type=int, default=1)
    return parser.parse_args()


cfg = Config.fromDict({'savePath':'D:\\_ARCHIVE\\E_BELOW50000\\'})
setGlobalConfig(cfg)
args = parse_args()


# 糊成一坨了
class WordWrapDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole)
        if not text:
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setPlainText(text)  # 不改原内容，不解析 HTML
        doc.setTextWidth(option.rect.width())

        return QSize(int(doc.idealWidth()), int(doc.size().height()) + 12)

    def paint(self, painter, option, index):
        painter.save()
        text = index.data(Qt.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setDefaultFont(option.font)
            doc.setPlainText(text)
            doc.setTextWidth(option.rect.width())

            painter.translate(option.rect.x(), option.rect.y())
            doc.drawContents(painter)
        else:
            # 没有文本时调用默认绘制（比如选中状态）
            super().paint(painter, option, index)
        painter.restore()


def renderMentionSafe(text):
    return re.sub(
        r'\[(@[^]]*?)]\(https?://www\.ottohub\.cn/u/(\d+)/?\)',
        r'@ou\2',
        text
    )


class MainWin(QtWidgets.QMainWindow, viewer.UiMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self, content='', uid=0, title='', pub_time_f='', arc_time_f='', view=0, fav=0, like=0,
                     comments=[], channel_id=0, gore='', tag_str='', attach_vid=0, initial=args.bid)
        self.btnLoad.clicked.connect(self.renderObarc)
        shortcut = QShortcut(QKeySequence("F7"), self)
        shortcut.activated.connect(self.renderObarc)
        # self.commentTree.setItemDelegateForColumn(1, WordWrapDelegate(self.commentTree))

    def renderObarc(self):
        bid = self.numOid.value()
        b_path = f'D:\\_ARCHIVE\\E_BELOW50000\\ob{bid}.obarc'
        if not os.path.exists(b_path):
            succ, data = self.extractFrom7z(bid)
            if not succ:
                QMessageBox.warning(self, "文件不存在",
                                    f"ob{bid}.obarc 不存在，且无法从压缩包解压。\n"
                                    f"请检查存档目录。")
                return
            else:
                b = loadObarcBytes(data)
        else:
            b = loadObarc(bid)
        try:
            pf = formatTime(b.timestamp)
            af = formatTime(b.arc_time)
            comments = b.comments
            self.commentTree.clear()
            self.addComments(self.commentTree, comments)
            self.retranslateUi(self, content=b.content.replace('\n', '<br>'), uid=b.uid, title=b.title,
                               pub_time_f=pf, arc_time_f=af,
                               view=b.view_count, fav=b.favorite_count, like=b.like_count,
                               channel_id=b.channel_id if b.channel_id != 0 else "无",
                               gore='4000+' if b.is_gore else '8+',
                               tag_str='; '.join(b.tags) if len(b.tags)!=0 else '无', attach_vid=b.attached_vid,
                               )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载 ob{bid} 失败:\n{str(e)}")

    def extractFrom7z(self, bid):
        start = (bid - 1) // 100 * 100 + 1
        end = start + 99
        archive_path = f'D:/_ARCHIVE/OTTO/ob{start}~ob{end}.7z'
        if not os.path.exists(archive_path):
            return False, None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with py7zr.SevenZipFile(archive_path, 'r') as z:
                    z.extract(targets=[f'ob{bid}.obarc'], path=tmpdir)

                file_path = os.path.join(tmpdir, f'ob{bid}.obarc')
                with open(file_path, 'rb') as f:
                    data = f.read()
            return True, data
        except Exception as e:
            QMessageBox.critical(self, '错误', f"解压失败: {e}")
            return False, None

    def addComments(self, par, comments):
        for comment in comments:
            item = QTreeWidgetItem(par)
            item.setText(0, f"ou{comment.uid}")
            # item.setText(1, comment.content)
            # [@昵称](https://www.ottohub.cn/u/uid) -> @ouuid
            item.setText(1, renderMentionSafe(comment.content))

            item.setText(2, formatTime(comment.timestamp))
            # 递归子评论
            if comment.replies:
                self.addComments(item, comment.replies)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = MainWin()
    widget.show()
    app.exec_()
    # sys.exit(app.exec_())
