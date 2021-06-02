#!/usr/bin/env python3

import re

import telebot

from db_hndlr import DBHndlr


class InputHndlr:
    """form input handler"""
    COMMENT_STATUS = -1
    UPLOAD_STATUS = -2
    SPECIAL_STATUSES = {COMMENT_STATUS, UPLOAD_STATUS}

    def __init__(self, tg_bot, db_hndlr, form_keys, cols, msg, report_file_addr, comments_file_addr, db_config):
        self.tg_bot = tg_bot
        self.db_hndlr = db_hndlr
        self.form_keys = form_keys
        self.cols = cols
        self.msg = msg
        self.report_file_addr = report_file_addr
        self.comments_file_addr = comments_file_addr
        self.db_config = db_config
        self.IDLE_STATUS = len(self.cols)

    def is_valid_msg(self, msg, index):
        if self.cols[index][self.form_keys.choices] and not self.cols[index][self.form_keys.mask]:
            return msg in set(map(self.normalize, self.cols[index][self.form_keys.choices]))
        else:
            if msg == "":
                msg = "."
            return re.fullmatch(pattern=self.cols[index][self.form_keys.mask], string=msg)

    def get_reply_markup(self, index):
        if self.cols[index][self.form_keys.choices]:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            for i in self.cols[index][self.form_keys.choices]:
                markup.add(telebot.types.KeyboardButton(i))
            return markup
        else:
            return telebot.types.ReplyKeyboardRemove()

    def get_report(self, uid):
        res = ""
        for col in self.cols:
            res += "%s %s:\t%s\n" % (
                self.msg.list_sign,
                col[self.form_keys.report_key],
                self.prettify(self.db_hndlr.get_attr(uid, col[self.form_keys.db_key])))
        return res

    def prettify(self, text):
        if not text:
            text = ""
        return text

    def normalize(self, text):
        text = text.replace("۰", "0")
        text = text.replace("۱", "1")
        text = text.replace("۲", "2")
        text = text.replace("۳", "3")
        text = text.replace("۴", "4")
        text = text.replace("۵", "5")
        text = text.replace("۶", "6")
        text = text.replace("۷", "7")
        text = text.replace("۸", "8")
        text = text.replace("۹", "9")
        text = text.replace("ي", "ی")
        text = text.replace("ك", "ک")
        if text.strip() == ".":
            text = ""
        return text

    def msg_handlr(self, msg):
        usr_id = msg.from_user.id
        chat_id = msg.chat.id
        username = msg.from_user.username
        text = self.normalize(msg.text)
        status = self.db_hndlr.get_status(usr_id)

        if text == "/start" or status == DBHndlr.CellNotFound:
            if not self.db_hndlr.existed(usr_id):
                self.db_hndlr.create_row(usr_id, chat_id)
            status = 0
            self.db_hndlr.set_status(usr_id, status)
            self.db_hndlr.set_attr(usr_id, self.db_config.username_key, username)
            self.tg_bot.send_message(chat_id, self.msg.start)
        elif status == self.UPLOAD_STATUS:
            self.handle_upload(msg)
        elif status == self.COMMENT_STATUS:
            self.handle_comment(msg)
        elif status == self.IDLE_STATUS:
            pass
        else:
            if(
                self.is_valid_msg(msg=text, index=status)
                and self.db_hndlr.set_attr(usr_id, self.cols[status][self.form_keys.db_key], text)
            ):
                status += 1
                self.db_hndlr.set_status(usr_id, status)
            else:
                self.tg_bot.send_message(chat_id, self.msg.e422)

        if status < len(self.cols) and status not in self.SPECIAL_STATUSES:
            self.tg_bot.send_message(
                chat_id,
                self.cols[status][self.form_keys.msg],
                reply_markup=self.get_reply_markup(status))
        elif status in self.SPECIAL_STATUSES:
            pass
        else:
            self.tg_bot.send_message(chat_id, self.msg.done + self.get_report(usr_id))

    def handle_comment(self, msg):
        chat_id = msg.chat.id
        username = msg.from_user.username
        text = self.normalize(msg.text)
        if self.db_hndlr.add_commnet(chat_id, username, text):
            self.tg_bot.send_message(chat_id, self.msg.tnx)

    def handle_upload(self, msg):
        usr_id = msg.from_user.id
        chat_id = msg.chat.id
        username = msg.from_user.username
        # TODO save file
        self.tg_bot.send_message(chat_id, self.msg.tnx)

    def send_about(self, msg):
        chat_id = msg.chat.id
        self.tg_bot.send_message(chat_id, self.msg.about)

    def send_upload_info(self, msg):
        usr_id = msg.from_user.id
        chat_id = msg.chat.id
        if not self.db_hndlr.existed(usr_id):
            self.db_hndlr.create_row(usr_id, chat_id)
        status = self.UPLOAD_STATUS
        self.db_hndlr.set_status(usr_id, status)
        self.tg_bot.send_message(chat_id, self.msg.upload)

    def send_comment_info(self, msg):
        usr_id = msg.from_user.id
        chat_id = msg.chat.id
        if not self.db_hndlr.existed(usr_id):
            self.db_hndlr.create_row(usr_id, chat_id)
        status = self.COMMENT_STATUS
        self.db_hndlr.set_status(usr_id, status)
        self.tg_bot.send_message(chat_id, self.msg.cmt)

    def send_report(self, msg):
        usr_id = msg.from_user.id
        chat_id = msg.chat.id

        if msg.from_user.username in self.tg_bot.admins:
            self.db_hndlr.export(self.report_file_addr)
            with open(self.report_file_addr, "rb") as f:
                self.tg_bot.send_document(chat_id, f)
            self.db_hndlr.export_comments(self.comments_file_addr)
            with open(self.comments_file_addr, "rb") as f:
                self.tg_bot.send_document(chat_id, f)
        elif not self.db_hndlr.existed(usr_id):
            self.tg_bot.send_message(chat_id, self.msg.nodata)
        else:
            self.tg_bot.send_message(chat_id, self.get_report(usr_id))
