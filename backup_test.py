import requests
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs


START_URL = "https://music.163.com/discover/toplist?id=3778678"  # 随便选一个已知榜单 ID

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


def build_songs_csv(genre_charts, output_path=None):
    if output_path is None:
        output_path = Path(__file__).parent / "data" / "songs.csv"

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

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    charts = fetch_all_toplist_links()
    genre_charts = filter_genre_charts(charts)
    for chart in genre_charts:
        print(chart["id"], chart["name"], chart["genre"], chart["url"])

    if genre_charts:
        first = genre_charts[0]
        songs = fetch_songs_from_chart(first["url"], first["genre"])
        for song in songs[:10]:
            print(song["title"], "-", song["artist"], "/", song["genre"])

    output_path = build_songs_csv(genre_charts)
    print("songs.csv 已生成:", output_path)