import tkinter as tk
import tkinter.ttk as ttk
import util as ut
import re

stickyall = (tk.W, tk.E, tk.N, tk.S)
stickyY = (tk.N, tk.S)
stickyX = (tk.W, tk.E)


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.finds = None  # 検索結果のバッファ
        self.find_indexces_list = None  # ヒットした行のインデックスのバッファ
        self.filepaths = ut.get_db_paths()  # データベースのパス
        self.last_update_path = self.filepaths[0]  # 最後に更新したデータベースのパス
        self.listbox_db_idx_map = {}  # dict{listbox_idx: db_idx}
        self.db = ut.Textdb(self.filepaths)  # データベース作成
        self.pack(side="top", anchor=tk.NW, expand=True, fill=tk.BOTH)
        # ---ウィジェットの引き伸ばし設定
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.create_widgets()
        self.display_all()

    def create_widgets(self):
        # ------Entry関係
        # ---親Frame1
        self.fr1 = tk.Frame(self, borderwidth=1, relief=tk.GROOVE)  # フレーム
        self.fr1.grid(row=1, column=0, padx=5, pady=0, sticky=stickyall)
        self.fr1.columnconfigure(0, weight=1)
        self.fr1.bind("<Key>", self.key)

        # ---Entry
        self.entry_var = tk.StringVar()
        self.entry_var.trace(
            "w", lambda name, index, mode, sv=self.entry_var: self.search_main()
        )
        self.en = tk.Entry(self.fr1, textvariable=self.entry_var)
        self.en.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))  # 表示メソッド
        self.en.bind("<KeyPress-F5>", lambda e: self.reload_database())
        self.en.bind("<Control-KeyPress-n>", lambda e: self.openDialog())
        self.en.focus_set()

        # ------親Frame2
        self.fr2 = tk.Frame(self, borderwidth=1, relief=tk.GROOVE)  # フレーム
        self.fr2.grid(row=2, column=0, padx=5, pady=5, sticky=stickyall)
        # ---ウィジェットの引き伸ばし設定(0行目無効化, # 0, 1列目を均等引き延ばし)
        self.fr2.rowconfigure(0, weight=1)
        self.fr2.columnconfigure(0, weight=1, uniform="group1")
        self.fr2.columnconfigure(2, weight=1, uniform="group1")

        # ---リストボックス
        self.lbox_string = tk.StringVar()  # 文字列なのでStringVar()でオブジェクトを生成
        self.lbox = tk.Listbox(self.fr2, listvariable=self.lbox_string)
        self.lbox.grid(row=0, column=0, padx=0, pady=5, sticky=stickyall)  # リストボックス配置
        self.lbox.bind("<<ListboxSelect>>",
            lambda e: self.selection_print_to_TextFrame(),
        )  # 項目が選択されたときの処理
        self.lbox.bind("<Control-KeyPress-d>", lambda e: self.remove_block())
        self.lbox.bind("<Control-KeyPress-s>", lambda e: self.save_changed())

        # スクロールバーの生成・配置
        self.scbar = tk.Scrollbar(self.fr2, orient=tk.VERTICAL, command=self.lbox.yview)
        self.scbar.grid(row=0, column=1, padx=0, pady=5, sticky=stickyY)
        self.lbox["yscrollcommand"] = self.scbar.set

        # テキストボックス
        self.tbox = tk.Text(self.fr2)  # fr内に配置
        self.tbox.tag_configure(
            "highlight", background="yellow", foreground="black"
        )  # 強調表示タグ生成
        self.tbox.bind("<Control-KeyPress-s>", lambda e: self.save_edit_text())
        self.tbox.grid(row=0, column=2, padx=5, pady=5, sticky=stickyall)

        # # ボタンの生成・配置
        # button_page = ttk.Button(root, text="+", width=4)
        # button_page.bind("<1>", lambda event: self.lbox.insert(tk.END, "新規"))
        # button_page.pack()

        # # ボタン
        # self.bt = tk.Button(self)
        # self.bt["text"] = "ボタン"
        # self.bt["command"] = self.buttontest
        # self.bt.pack(side="bottom")

    def openDialog(self):
        self.dialog = tk.Toplevel(self)  # サブウィンドウ作成
        self.dialog.title("データ追加")
        self.dialog.grab_set()
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(1, weight=1)

        # ---combobox
        combo_files = ttk.Combobox(self.dialog, state="readonly")
        combo_files["values"] = self.filepaths
        combo_files.current(
            self.filepaths.index(self.last_update_path)
        )  # 最後に更新したパスをデフォルトにする
        combo_files.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))  # 表示メソッド

        # ---追加データ入力用テキストボックス
        tbox_append = tk.Text(self.dialog)  # fr内に配置
        tbox_append.grid(row=1, column=0, padx=5, pady=5, sticky=stickyall)
        tbox_append.focus_set()

        # closeする前にダイアログに入力された値を反映する
        def closeDialog():
            self.last_update_path = combo_files.get()  # 最終更新ファイルパスを更新
            self.db.append_block(
                self.last_update_path, tbox_append.get("1.0", "end")
            )  # 書き込み
            self.dialog.destroy()
            self.reload_database()

        tbox_append.bind("<Control-KeyPress-Return>", lambda e: closeDialog())

    def search_main(self):
        # dbからentryのtextを検索してリストボックスに入れる
        query = self.en.get()
        if query == "":  # 空になった時の処理
            self.find_indexces_list = None
            self.display_all()
            return

        self.finds = self.db.search2(self.en.get(), True)
        self.find_indexces_list = list(self.finds.values())
        self.blocklist = self.db[self.finds.keys()]
        self.listbox_db_idx_map = {n:k for n,k in enumerate(self.finds.keys())}

        self.update_listbox(self.lbox_string, self.blocklist)

        if len(self.blocklist) > 0:
            self.update_textbox(
                self.blocklist[0], self.find_indexces_list[0]
            )
        else:
            self.tbox.delete("1.0", "end")

    def reload_database(self):
        # self.db = ut.Textdb(self.filepaths)
        self.search_main()

    def display_all(self):
        # 全検索結果を適用
        self.listbox_db_idx_map = {n:k for n,k in enumerate(self.db.db.keys())}
        self.update_listbox(self.lbox_string, list(self.db.db.values()))
        self.update_textbox(self.db.db[0])

    def save_edit_text(self):
        # リストボックスで選択したテキスト取得
        selected_idx = self.lbox.curselection()[0]
        new_block = re.findall(".*\n", self.tbox.get("1.0", "end"))
        db_idx = self.listbox_db_idx_map[selected_idx] # dbのidxに変換
        self.db.change_block(db_idx, new_block, True)
        self.reload_database()
        self.selection_print_to_TextFrame()

    def remove_block(self):
        # リストボックスで選択したテキスト取得
        selected_idx = self.lbox.curselection()[0]
        db_idx = self.listbox_db_idx_map[selected_idx] # dbのidxに変換
        self.db.remove_block(db_idx, False)
        self.reload_database()
        self.selection_print_to_TextFrame()

    def save_changed(self):
        self.db.save_changed_files()

    def selection_print_to_TextFrame(self):
        # リストボックスで選択したテキスト取得
        selected_idx = self.lbox.curselection()
        if len(selected_idx) == 0:
            return
        selected_idx = selected_idx[0]
        words = self.lbox.get(selected_idx)
        if self.find_indexces_list:
            self.update_textbox(words, self.find_indexces_list[selected_idx])
        else:
            self.update_textbox(words)

    def update_textbox(self, words, find_indexces=None):
        # tBoxをにwordsで上書き
        self.tbox.delete("1.0", "end")
        [self.tbox.insert(tk.INSERT, word) for word in words]
        # ヒット行のハイライト
        if find_indexces: 
            for i in find_indexces:
                self.tbox.tag_add(
                    "highlight", "{}.0".format(i + 1), "{}.0+1lines".format(i + 1)
                )

    def update_listbox(self, lbox: tk.Listbox, values):
        lbox.set(values)

    def key(self, event):
        print("pressed", repr(event.char))


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.title("search")
    root.mainloop()
