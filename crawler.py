from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

# 生成模拟爬虫结构，防止爬取失败时候备用
def generate_sample_dataset(csv_path: Path | None = None) -> Path:
    """生成一个示例歌曲数据集，模拟爬虫的结果。

    实际项目中可以使用 requests + BeautifulSoup 等库，从真实音乐网站
    爬取歌曲信息，然后整理为与本函数生成的数据格式一致的 CSV。
    """
    if csv_path is None:
        csv_path = Path(__file__).parent / "data" / "songs.csv"

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        {"id": 1, "title": "Shape of You", "artist": "Ed Sheeran", "genre": "Pop"},
        {"id": 2, "title": "Perfect", "artist": "Ed Sheeran", "genre": "Pop"},
        {"id": 3, "title": "Blinding Lights", "artist": "The Weeknd", "genre": "Pop"},
        {"id": 4, "title": "Save Your Tears", "artist": "The Weeknd", "genre": "Pop"},
        {"id": 5, "title": "Bad Guy", "artist": "Billie Eilish", "genre": "Pop"},
        {"id": 6, "title": "Lovely", "artist": "Billie Eilish", "genre": "Pop"},
        {"id": 7, "title": "Rolling in the Deep", "artist": "Adele", "genre": "Pop"},
        {"id": 8, "title": "Someone Like You", "artist": "Adele", "genre": "Pop"},
        {"id": 9, "title": "Counting Stars", "artist": "OneRepublic", "genre": "PopRock"},
        {"id": 10, "title": "Believer", "artist": "Imagine Dragons", "genre": "Rock"},
        {"id": 11, "title": "Radioactive", "artist": "Imagine Dragons", "genre": "Rock"},
        {"id": 12, "title": "Faded", "artist": "Alan Walker", "genre": "EDM"},
        {"id": 13, "title": "Alone", "artist": "Alan Walker", "genre": "EDM"},
        {"id": 14, "title": "告白气球", "artist": "周杰伦", "genre": "Mandopop"},
        {"id": 15, "title": "七里香", "artist": "周杰伦", "genre": "Mandopop"},
        {"id": 16, "title": "稻香", "artist": "周杰伦", "genre": "Mandopop"},
        {"id": 17, "title": "年少有为", "artist": "李荣浩", "genre": "Mandopop"},
        {"id": 18, "title": "平凡之路", "artist": "朴树", "genre": "Mandopop"},
        {"id": 19, "title": "夜空中最亮的星", "artist": "逃跑计划", "genre": "Mandopop"},
        {"id": 20, "title": "演员", "artist": "薛之谦", "genre": "Mandopop"},
    ]

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path

# 默认的开始地址，为了拿到全部的HTML
START_URL = "https://music.163.com/discover/toplist?id=3778678"

# 榜单白名单
GENRE_CHARTS = {
    "网易云中文说唱榜": "中文说唱",
    "网易云全球说唱榜": "说唱",
    "网易云古典榜": "古典",
    "网易云电音榜": "电音",
    "网易云ACG榜": "ACG",
    "网易云ACG动画榜": "ACG",
    "网易云ACG游戏榜": "ACG",
    "网易云ACG　VOCALOID榜": "ACG",
    "网易云韩语榜": "Korean",
    "网易云日语榜": "Japanese",
    "俄语榜": "Russian",
    "越南语榜": "Vietnamese",
    "泰语榜": "Thai",
    "网易云摇滚榜": "Rock",
    "网易云民谣榜": "Folk",
    "网易云国风榜": "国风",
    "欧美R&B榜": "R&B",
    "Beatport全球电子舞曲榜": "EDM",
    "中文慢摇DJ榜": "DJ",
}

# 获取全部的榜单url
def fetch_all_toplist_links():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://music.163.com/",
    }
    resp = requests.get(START_URL, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    left_nav = soup

    for a in left_nav.select('a[href*="/discover/toplist?id="]'):
        name = a.get_text(strip=True)
        href = a.get("href")
        if not href:
            continue

        full_url = urljoin(START_URL, href)

        qs = parse_qs(urlparse(full_url).query)
        chart_id = qs.get("id", [None])[0]
        if not chart_id:
            continue

        links.append(
            {
                "id": chart_id,
                "name": name,
                "url": full_url,
            }
        )

    uniq = {}
    for item in links:
        uniq[item["id"]] = item
    result = list(uniq.values())
    print(f"共发现 {len(result)} 个排行榜")
    return result

# 筛选出有用的风格榜单
def filter_genre_charts(charts):
    result = []
    for chart in charts:
        name = chart["name"]
        genre = GENRE_CHARTS.get(name)
        if genre is None:
            continue
        item = chart.copy()
        item["genre"] = genre
        result.append(item)
    print(f"其中保留 {len(result)} 个风格榜单")
    return result

# 通过筛选出来的榜单地址获取JSON，调用官方的API接口，返回{歌名、作者、风格}列表
def fetch_songs_from_chart(chart_url, genre, session=None):
    if session is None:
        session = requests.Session()

    parsed = urlparse(chart_url)
    qs = parse_qs(parsed.query)
    playlist_id = qs.get("id", [None])[0]
    if not playlist_id:
        raise ValueError(f"无法从 URL 中解析榜单 id: {chart_url}")

    api_url = f"https://music.163.com/api/playlist/detail?id={playlist_id}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": chart_url,
    }

    resp = session.get(api_url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    tracks = (data.get("result") or {}).get("tracks") or []
    songs = []

    for track in tracks:
        title = (track.get("name") or "").strip()
        if not title:
            continue

        artists = track.get("artists") or []
        artist_names = "/".join(
            a.get("name", "").strip() for a in artists if a.get("name")
        )

        songs.append(
            {
                "title": title,
                "artist": artist_names,
                "genre": genre,
            }
        )

    return songs

# 将数据保存在CSV文件中
def build_songs_csv(genre_charts, csv_path: Path | None = None) -> Path:
    if csv_path is None:
        csv_path = Path(__file__).parent / "data" / "songs.csv"

    session = requests.Session()
    rows = []
    seen = set()

    for chart in genre_charts:
        chart_url = chart["url"]
        chart_genre = chart["genre"]
        songs = fetch_songs_from_chart(chart_url, chart_genre, session=session)
        print(f"{chart['name']} ({chart_genre}) -> {len(songs)} 首")
        for song in songs:
            key = (song["title"], song["artist"], song["genre"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(song)

    df = pd.DataFrame(rows)
    if not df.empty:
        df.insert(0, "id", range(1, len(df) + 1))
    print(f"最终汇总 {len(rows)} 首歌曲")

    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path


def generate_dataset_from_netease(csv_path: Path | None = None) -> Path:
    charts = fetch_all_toplist_links()
    genre_charts = filter_genre_charts(charts)
    return build_songs_csv(genre_charts, csv_path=csv_path)


if __name__ == "__main__":
    try:
        output_path = generate_dataset_from_netease()
        print(f"网易云数据已生成: {output_path}")
    except Exception:
        output_path = generate_sample_dataset()
        print(f"示例歌曲数据已生成: {output_path}")
