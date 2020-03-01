import os
import itertools
import glob
import re

debugfilepaths = glob.glob("dbdir/*.txt")



def lastone(iterable):
    it = iter(iterable)
    last = next(it)
    for val in it:
        yield last, False
        last = val
    yield last, True

def get_db_paths(dirpath="dbdir"):
    ret_paths = glob.glob(dirpath + "/*.txt")
    return ret_paths


class Textdb:
    def __init__(self, filepaths):
        # 検索は小文字データベースから行う(大文字小文字の区別が出来ないため)
        self.__db, self.path_idx_map = self.make_db(filepaths)
        self.db_small = {
            n: [line.lower() for line in block] for n, block in self.db.items()
        }
        self.delimiter = "\n"  # 文字×行数
        self.delimiter_num = 3  # 文字×行数
        self.changed_files = []

    # blockを取得
    # 単一インデックス、iterableインデックスに対応
    def __getitem__(self, indexes):
        if type(indexes) != list:
            if hasattr(indexes, "__iter__"):
                indexes = list(indexes)
            else:
                indexes = [indexes]
        ret = [self.db[i] for i in indexes]

        return ret

    # idxからfilepathを取得
    def getpath_from_idx(self, idx):  # todo 高速化
        for path, indexces in self.path_idx_map.items():
            if idx in indexces:
                return path

    # idxのblockをnew_linesに変更
    def change_block(self, idx, new_lines, is_save=False):
        self.db[idx] = new_lines
        filepath = self.getpath_from_idx(idx)
        if is_save:
            newblocks = self.getblocks_from_path(filepath)
            self.__write_blocks(filepath, newblocks)
        else:
            if not filepath in self.changed_files:
                self.changed_files.append(filepath)

    # idxのblockを削除
    def remove_block(self, idx, is_save=False):
        self.db.pop(idx)
        self.db_small.pop(idx)
        filepath = self.getpath_from_idx(idx)
        self.path_idx_map[filepath].remove(idx)
        if is_save:
            newblocks = self.getblocks_from_path(filepath)
            self.__write_blocks(filepath, newblocks)
        else:
            if not filepath in self.changed_files:
                self.changed_files.append(filepath)

    def save_changed_files(self):
        for p in self.changed_files:
            newblocks = self.getblocks_from_path(p)
            self.__write_blocks(p, newblocks)

    # ファイルパスからblocksを取得
    def getblocks_from_path(self, filepath):
        ret = self[self.path_idx_map[filepath]]
        return ret

    # filepathにblocksを書き込み
    def __write_blocks(self, filepath, blocks):
        with open(filepath, "w", encoding="utf-8") as f:
            for block, is_last in lastone(blocks):
                if not is_last:
                    f.writelines(block + [self.delimiter * self.delimiter_num])
                else:
                    f.writelines(block)

    def append_block(self, filepath, lines):
        if type(lines) != list:  # 改行でsplitしたリストに変換
            lines = re.findall(".*\n", lines)
        new_key = max(self.db.keys())+1
        self.db[new_key] = lines
        self.db_small[new_key] = [line.lower() for line in lines]
        self.path_idx_map[filepath].append(new_key)

        """ filepathにlinesを付加する。 """
        if not os.path.exists(filepath):
            print("{}is not found.".format(filepath))
            return


        # ファイルの末尾にデリミタが存在するか確認。無ければ追加する。
        with open(filepath, "a+", encoding="utf-8") as f:  # 読み書きモード
            f.seek(0)  # ファイルポインタをファイル先頭へ
            lastlines = f.readlines()[-self.delimiter_num :]
            for n, line in enumerate(reversed(lastlines)):
                if line != self.delimiter:
                    if not ("\n" in lastlines[-1]):  # 最終行に改行が無ければ追加
                        lines.insert(0, "\n")
                    lines.insert(0, self.delimiter * (self.delimiter_num - n))
                    break
            f.writelines(lines)

    def make_db(self, filepath):
        """"
            改行3つで区切った文字列のリストを生成
        """

        # ------パスのテキストをdelimでブロック単位にsplit。インデックスでマッピング。
        delimiter = "\n"
        delim_threas = 3  # dlimiterがこの回数以上連続で出てきた場合、splitする。
        block_count = 0  # 抽出したブロックのカウンタ
        next_start_map_count = 0
        pathlist_len = len(filepath)
        idx_block_map = {}  # dict{block_index: block}
        path_idx_map = {}  # dict{path: list(block_index)}
        for m, p in enumerate(filepath):
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # ---改行コード×delim_threasでsplitする処理。
            delimcount = 0  # \nが出てきた回数
            next_start_idx = 0  # 次回の開始インデックス
            for n, line in enumerate(lines):
                if line == delimiter:
                    delimcount += 1
                    if delimcount == delim_threas:  # \nがsplit回数出たらstr抽出、カウンタ類をリセット、更新
                        idx_block_map[block_count] = lines[
                            next_start_idx : n - delim_threas + 1
                        ]
                        next_start_idx = n + 1
                        delimcount = 0
                        block_count += 1
                else:
                    delimcount = 0

                # ---最後のファイルかつ最終ブロックの場合。残りを全て入れる
                if n == (len(lines) - 1):
                    idx_block_map[block_count] = lines[next_start_idx:]
                    block_count += 1

            path_idx_map[p] = [i for i in range(next_start_map_count, block_count)]
            next_start_map_count = block_count

        return idx_block_map, path_idx_map

    def __make_db_proto(self, filepath):
        """"
            改行3つで区切った文字列のリストを生成
        """

        # ------パスのテキストをdelimでブロック単位にsplit。インデックスでマッピング。
        delimiter = "\n"
        delim_threas = 3  # dlimiterがこの回数以上連続で出てきた場合、splitする。
        next_start_map_count = 0
        pathlist_len = len(filepath)
        idx_path_map = {}  # dict{path: list(block_index)}
        idx_blocks_map = []
        for m, p in enumerate(filepath):
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # ---改行コード×delim_threasでsplitする処理。
            delimcount = 0  # \nが出てきた回数
            next_start_idx = 0  # 次回の開始インデックス
            _idx_block_map = []
            for n, line in enumerate(lines):
                if line == delimiter:
                    delimcount += 1
                    if delimcount == delim_threas:  # \nがsplit回数出たらstr抽出、カウンタ類をリセット、更新
                        _idx_block_map.append(
                            lines[next_start_idx : n - delim_threas + 1]
                        )
                        next_start_idx = n + 1
                        delimcount = 0
                else:
                    delimcount = 0

                # ---最後のファイルかつ最終ブロックの場合。残りを全て入れる
                if n == (len(lines) - 1):
                    _idx_block_map.append(lines[next_start_idx:])

            idx_path_map[m] = p
            idx_blocks_map.append(_idx_block_map)

        return idx_blocks_map, idx_path_map

    def search2(self, query, get_find_indexces=False):
        _query = query.lower()  # 小文字変換
        retdic = {}

        for n, datas in self.db_small.items():  # 小文字データベースから検索
            hit_line_idx = []
            for m, lines in enumerate(datas):  # データのlines取得
                if _query in lines:  # 検索対象が見つかればリストに追加
                    hit_line_idx.append(m)
            if len(hit_line_idx) > 0:
                retdic[n] = hit_line_idx

        return retdic

    @property
    def db(self):
        return self.__db


if __name__ == "__main__":
    db = Textdb(debugfilepaths)
    # db.change_block(15, ["bb\n", "cc\n"], True)
    # a = db.search2("git")
    # b = db.getpath_from_idx(1)
    # db.append_block("huge.txt", ["hoge\n", "huga"])
