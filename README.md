# 基于爬虫 + AI 轻量化模型的音乐推荐系统

本项目使用 **Python + Flask + scikit-learn** 实现了一个内容相似度驱动的音乐推荐小系统，主要用于课程实验 / 学习演示。

整体思路：

1. 通过爬虫（或模拟爬虫）获取歌曲数据，保存到 `data/songs.csv`。
2. 利用 TF-IDF 提取每首歌的文本特征（如歌名、歌手、风格等拼接形成的文本）。
3. 使用余弦相似度计算歌曲之间的相似度，得到“相似歌曲列表”。
4. 通过 Flask 提供 Web 页面：
   - 首页：让用户选择自己喜欢的歌曲。
   - 结果页：基于已选歌曲，推荐若干相似歌曲并展示相似度评分。

---

## 一、环境依赖

- Python 3.10 或以上版本
- 依赖包见 `requirements.txt`，主要包括：
  - Flask：Web 框架
  - pandas、numpy：数据处理
  - scikit-learn：TF-IDF、余弦相似度等

在项目根目录执行以下命令安装依赖：

```bash
pip install -r requirements.txt
```

---

## 二、运行方式

1. 确保当前目录为项目根目录（包含 `app.py`）。
2. 在终端 / 命令行中执行：

   ```bash
   python app.py
   ```

3. 看到类似输出：

   ```
   * Running on http://127.0.0.1:5000
   ```

4. 打开浏览器，访问：

   ```
   http://127.0.0.1:5000/
   ```

5. 交互流程：
   - 在首页从歌曲列表中选择一首或多首你喜欢的歌曲（按住 Ctrl/Shift 可多选）。
   - 点击“生成推荐”按钮，向后端提交表单。
   - 在推荐结果页面中查看系统给出的相似歌曲列表及相似度分数。

---

## 三、系统功能与特点

- **基础功能**
  - 展示多种风格的歌曲列表，用户可多选。
  - 基于内容相似度（TF-IDF + 余弦相似度）生成推荐结果。
  - 显示用户已选歌曲和推荐歌曲的歌名、歌手、风格及相似度分数。

- **错误处理**
  - 若用户未选择任何歌曲，自动跳转回首页并显示错误提示。
  - 若选择的歌曲不在歌曲库中，也会给出友好的错误信息。

- **界面**
  - 使用基础 HTML + CSS，提供简单但相对美观的选择页与结果页。

---

## 四、Flask 工作流程与路由说明

### 1. 启动应用

在 `app.py` 中：

```python
app = Flask(__name__)

if __name__ == "__main__":
    app.run(debug=True)
```

- `app = Flask(__name__)` 创建一个 Flask 应用对象。
- 直接运行 `python app.py` 时，`__name__ == "__main__"` 为真，执行 `app.run(debug=True)`，
  启动开发服务器，默认监听地址为 `http://127.0.0.1:5000/`。

### 2. 首页路由：展示可选歌曲

```python
@app.route("/", methods=["GET"])
def index():
    songs_df = recommender.get_display_songs(max_per_genre=4)
    songs = songs_df.to_dict(orient="records")
    error = request.args.get("error")
    return render_template("index.html", songs=songs, error=error)
```

- 路径 `/` 对应网站根路径，即访问 `http://127.0.0.1:5000/` 时会调用 `index()`。
- `recommender.get_display_songs` 从数据集中按风格抽取部分歌曲，用于首页展示。
- 通过 `render_template("index.html", ...)` 渲染模板，将歌曲列表和错误信息传给前端页面。

### 3. 推荐路由：接收表单 + 生成推荐

```python
@app.route("/recommend", methods=["POST"])
def recommend_route():
    selected_titles = request.form.getlist("favorite_titles")
    if not selected_titles:
        return redirect(url_for("index", error="请至少选择一首歌曲。"))

    try:
        recommendations_df = recommender.recommend_by_titles(selected_titles, top_k=10)
    except ValueError as exc:
        return redirect(url_for("index", error=str(exc)))

    songs_df = recommender.get_all_songs()
    favorites_df = songs_df[songs_df["title"].isin(selected_titles)]

    favorites = favorites_df.to_dict(orient="records")
    recommendations = recommendations_df.to_dict(orient="records")
    return render_template(
        "result.html",
        favorites=favorites,
        recommendations=recommendations,
    )
```

- 路径 `/recommend` 对应表单提交接口，只接受 `POST` 请求。
- `request.form.getlist("favorite_titles")` 读取用户在首页多选框中选中的歌曲名列表。
- 若未选择任何歌曲，则通过 `redirect(url_for("index", error="..."))` 重定向回首页并提示错误。
- 调用 `recommender.recommend_by_titles` 生成推荐歌曲列表。
- 使用 `get_all_songs()` 得到完整歌曲信息，再根据选中的标题筛选出“用户已选的歌曲”。
- 将 `favorites` 与 `recommendations` 传给 `result.html` 模板，生成推荐结果页面。

---

## 五、推荐算法原理简介（recommender.py）

主要步骤如下：

1. **加载数据和模型**（`load_data_and_model`）
   - 若不存在 `data/songs.csv`，通过 `crawler.py` 生成示例数据。
   - 读取数据，构建 `pandas.DataFrame`。
   - 利用 `TfidfVectorizer` 对歌曲文本特征进行向量化，得到 `tfidf_matrix`。

2. **获取可展示的歌曲列表**（`get_display_songs`）
   - 按照歌曲风格 `genre` 分组，每个风格随机抽取最多 `max_per_genre` 首。
   - 返回包含 `id、title、artist、genre` 的子数据集，供首页展示使用。

3. **根据标题查找对应行索引**（`_find_indices_by_titles`）
   - 输入：若干歌曲标题。
   - 将标题统一转换为小写，在 DataFrame 中建立映射，找到每个标题对应的行索引。

4. **根据已选歌曲生成推荐**（`recommend_by_titles`）
   - 输入：用户选中的若干歌曲标题列表，参数 `top_k` 为返回的推荐数量。
   - 使用 `_find_indices_by_titles` 找到这些歌曲在 `tfidf_matrix` 中的索引。
   - 计算所选歌曲与所有歌曲的余弦相似度矩阵，并对多首歌的相似度取平均，得到每首候选歌的综合相似度分数。
   - 将用户已选的歌曲的相似度设为 -1（避免被推荐回去）。
   - 按相似度从高到低排序，取前 `top_k` 首作为推荐结果，附带 `score` 字段返回。

---

## 六、项目代码结构

- `app.py`：
  - Flask Web 应用入口，定义路由、请求处理逻辑，以及与推荐模块的交互。

- `recommender.py`：
  - 核心推荐算法模块，负责加载数据与模型、计算相似度、返回推荐结果。

- `crawler.py`：
  - 示例爬虫 / 数据生成脚本。
  - 当首次运行项目且 `data/songs.csv` 不存在时，用于生成一份示例歌曲数据。

- `data/` 目录：
  - 存放歌曲数据文件 `songs.csv`。

- `templates/` 目录：
  - `index.html`：首页模板，负责展示歌曲列表并提供表单选歌。
  - `result.html`：结果页模板，展示用户已选歌曲和推荐歌曲列表。

- `requirements.txt`：
  - 记录项目运行所需的 Python 依赖包及版本。

---

## 七、使用说明与注意事项

- 本项目为教学 / 课程实验用途，示例数据为手工或脚本生成，不涉及真实用户隐私。
- 开发模式下使用 `debug=True`，方便调试与自动重载，但**不建议在生产环境中开启**。
- 如需扩展：
  - 可以在 `songs.csv` 中增加更多字段（如专辑、年份、标签等）。
  - 可以在 `recommender.py` 中尝试其他相似度度量或融合多种特征。
  - 可以在 `templates/` 中美化前端页面或增加搜索等交互功能。

---

## 八、致谢

本项目仅用于学习和课程展示，欢迎在此基础上进行二次开发或改进，用于理解 Flask Web 开发与内容推荐算法的基本原理。

