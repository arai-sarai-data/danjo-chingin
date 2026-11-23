"""男女賃金差ランキング：厚生労働省「女性の活躍推進企業データベース」のオープンデータから、
企業が公表した「男女の賃金の差異」（男性を100としたときの女性の賃金）を並べる。"""
import re
from collections import defaultdict
from statistics import median

from lib import oc

PAGE = "https://positive-ryouritsu.mhlw.go.jp/positivedb/opendata/"
TOP = "https://positive-ryouritsu.mhlw.go.jp/positivedb/"


def load():
    urls = oc.links(PAGE, r"\.(csv|zip)(\?|$)")
    oc.check(urls, "オープンデータのファイルが見つかりません")
    frames = []
    for u in urls:
        b = oc.get(u, cache=re.sub(r"\W", "_", u)[-80:])
        if u.lower().split("?")[0].endswith(".zip"):
            for name, data in oc.unzip(b).items():
                if name.lower().endswith(".csv"):
                    frames.append(oc.read_csv(data))
        else:
            frames.append(oc.read_csv(b))
    for df in frames:  # 賃金の差異の列を持つ表を使う
        try:
            oc.col(df, "賃金", "差異")
            return df
        except Exception:
            continue
    raise oc.DataError("「男女の賃金の差異」の列を持つ表がありません")


def run():
    df = load()
    c_name = oc.col(df, "企業名")
    c_all = oc.col(df, "賃金", "差異", "全")
    c_reg = oc.col(df, "賃金", "差異", "正規", required=False)
    c_ind = oc.col(df, "業種", required=False)
    c_addr = oc.col(df, "所在地", required=False) or oc.col(df, "都道府県", required=False)
    c_size = oc.col(df, "労働者数", required=False) or oc.col(df, "従業員数", required=False)
    c_no = oc.col(df, "法人番号", required=False)
    rows = []
    for _, r in df.iterrows():
        v = oc.num(r[c_all])
        if v is None or not (5 <= v <= 300):
            continue
        rows.append({"co": str(r[c_name]).strip(), "gap": v, "reg": oc.num(r[c_reg]) if c_reg else None,
                     "ind": str(r[c_ind]).strip() if c_ind else "", "pref": oc.pref_of_address(str(r[c_addr])) if c_addr else "",
                     "size": oc.num(r[c_size]) if c_size else None,
                     "co_url": (TOP + "detail?id=" + str(r[c_no]).strip()) if c_no else ""})
    oc.check(len(rows) > 3000, "賃金の差異を公表した企業が少なすぎます(%d)" % len(rows))
    med = median(r["gap"] for r in rows)
    oc.check(40 <= med <= 95, "中央値が想定外です(%.1f)。単位が%%でない可能性" % med)

    cols = [{"key": "co", "label": "企業名", "type": "link"}, {"key": "gap", "label": "女性の賃金（男性=100）", "type": "num", "fmt": "1", "bar": True},
            {"key": "reg", "label": "うち正規雇用", "type": "num", "fmt": "1"}, {"key": "ind", "label": "業種"},
            {"key": "pref", "label": "所在地"}, {"key": "size", "label": "労働者数", "type": "num"}]
    big = [r for r in rows if (r["size"] or 0) >= 1000] or rows
    low = sorted(big, key=lambda r: r["gap"])
    high = sorted(big, key=lambda r: -r["gap"])
    agg = defaultdict(list)
    for r in rows:
        if r["ind"]:
            agg[r["ind"]].append(r["gap"])
    ind = sorted([{"ind": k, "med": round(median(v), 1), "n": len(v)} for k, v in agg.items() if len(v) >= 20], key=lambda r: r["med"])
    meth = ("女性活躍推進法により、労働者301人以上の企業は「男女の賃金の差異」（男性の平均賃金を100としたときの女性の平均賃金）を公表しています。"
            "その公表値をそのまま並べました。差異は同じ仕事の賃金差ではなく、管理職や正社員の男女比・勤続年数の違いを反映します。"
            "上位・下位は労働者1,000人以上の企業で比べています。")
    R = [{"id": "low", "tab": "差が大きい", "title": "女性の賃金が男性より低い企業（1,000人以上）",
          "desc": "男性を100としたときの女性の賃金（全労働者）が低い順。", "rows": low, "columns": cols, "method": meth,
          "trend": oc.trend(low, "ind", 50, "社", "社"), "share_label": "co", "share_value": "gap"},
         {"id": "high", "tab": "差が小さい", "title": "男女の賃金差が小さい企業（1,000人以上）",
          "desc": "女性の賃金が男性に近い（または上回る）順。", "rows": high, "columns": cols, "method": meth,
          "trend": oc.trend(high, "ind", 50, "社", "社"), "share_label": "co", "share_value": "gap"},
         {"id": "ind", "tab": "業種別", "title": "業種別の男女賃金差（中央値）",
          "desc": "公表企業が20社以上の業種。数字が小さいほど差が大きい。", "rows": ind, "method": meth,
          "columns": [{"key": "ind", "label": "業種"}, {"key": "med", "label": "女性の賃金（男性=100）の中央値", "type": "num", "fmt": "1", "bar": True},
                      {"key": "n", "label": "企業数", "type": "num"}], "share_label": "ind", "share_value": "med"}]
    meta = {"data_period": "各企業の最新の公表値",
            "stats": [{"label": "公表した企業", "value": len(rows), "unit": "社"},
                      {"label": "女性の賃金（男性=100）の中央値", "value": med, "fmt": "1"},
                      {"label": "男性の7割未満の企業", "value": sum(1 for r in rows if r["gap"] < 70), "unit": "社"}],
            "sources": [{"name": "女性の活躍推進企業データベース（オープンデータ）", "org": "厚生労働省", "url": PAGE, "license": "公共データ利用規約"}]}
    search = [{"n": r["co"], "s": r["ind"], "a": r["pref"], "u": r["co_url"],
               "k": [["女性の賃金（男性=100）", "%.1f" % r["gap"]]] + ([["正規雇用", "%.1f" % r["reg"]]] if r["reg"] else [])} for r in rows]
    oc.write(meta, R, search=search)


if __name__ == "__main__":
    oc.main(run)
