from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = Path(__file__).parent / "data" / "songs.csv"

_songs_df: pd.DataFrame | None = None
_tfidf_matrix = None
_vectorizer: TfidfVectorizer | None = None


def load_data_and_model():
    """加载歌曲数据并构建 TF-IDF 特征和相似度模型。"""
    global _songs_df, _vectorizer, _tfidf_matrix

    if _songs_df is not None and _tfidf_matrix is not None and _vectorizer is not None:
        return _songs_df, _vectorizer, _tfidf_matrix

    if not DATA_PATH.exists():
        # 如果数据文件不存在，自动生成一份示例数据
        from crawler import generate_dataset_from_netease, generate_sample_dataset

        try:
            generate_dataset_from_netease(DATA_PATH)
        except Exception:
            generate_sample_dataset(DATA_PATH)

    df = pd.read_csv(DATA_PATH, encoding="utf-8")

    required_cols = ["id", "title", "artist", "genre"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"数据缺少字段: {missing}")

    df = df.dropna(subset=["title"]).reset_index(drop=True)

    # 将标题、歌手、风格拼成一个文本字段，用于 TF-IDF
    df["combined"] = (
        df["title"].fillna("")
        + " "
        + df["artist"].fillna("")
        + " "
        + df["genre"].fillna("")
    )

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(df["combined"])

    _songs_df = df
    _vectorizer = vectorizer
    _tfidf_matrix = tfidf_matrix

    return _songs_df, _vectorizer, _tfidf_matrix


def get_all_songs():
    """返回所有歌曲的基本信息（用于页面展示）。"""
    df, _, _ = load_data_and_model()
    return df[["id", "title", "artist", "genre"]].copy()


def get_display_songs(max_per_genre: int = 30):
    df, _, _ = load_data_and_model()
    if max_per_genre is None or max_per_genre <= 0:
        return df[["id", "title", "artist", "genre"]].copy()

    sampled = (
        df.groupby("genre", group_keys=False)
        .apply(lambda g: g.sample(n=min(len(g), max_per_genre), random_state=42))
        .reset_index(drop=True)
    )
    return sampled[["id", "title", "artist", "genre"]].copy()


def _find_indices_by_titles(titles):
    """根据歌曲标题列表，找到对应的行索引。"""
    df, _, _ = load_data_and_model()
    title_to_index = {
        str(title_value).lower(): idx for idx, title_value in enumerate(df["title"])
    }
    indices = []
    for t in titles:
        idx = title_to_index.get(str(t).lower())
        if idx is not None:
            indices.append(idx)
    return indices


def recommend_by_titles(titles, top_k: int = 10):
    """根据若干首已知喜欢的歌曲，推荐相似歌曲。"""
    df, _, tfidf_matrix = load_data_and_model()

    if not titles:
        raise ValueError("请至少提供一首歌曲名称。")

    indices = _find_indices_by_titles(titles)
    if not indices:
        raise ValueError("提供的歌曲在歌曲库中不存在，请重新选择。")

    # 计算所选歌曲与所有歌曲的余弦相似度，并对多首歌取平均
    similarity_matrix = cosine_similarity(tfidf_matrix[indices], tfidf_matrix)
    mean_similarity = similarity_matrix.mean(axis=0)

    # 不推荐用户已经选择过的歌曲
    for idx in indices:
        mean_similarity[idx] = -1.0

    sorted_indices = mean_similarity.argsort()[::-1]
    top_indices = sorted_indices[:top_k]

    result_df = df.iloc[top_indices].copy()
    result_df["score"] = mean_similarity[top_indices]
    return result_df


if __name__ == "__main__":
    all_songs = get_all_songs()
    print("歌曲示例：")
    print(all_songs.head(10)[["title", "artist"]])

    test_titles = [all_songs.iloc[0]["title"]]
    print("\n根据以下歌曲推荐：", test_titles)
    rec_df = recommend_by_titles(test_titles, top_k=5)
    print(rec_df[["title", "artist", "genre", "score"]])
