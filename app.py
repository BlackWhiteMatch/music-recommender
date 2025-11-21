from flask import Flask, render_template, request, redirect, url_for

import recommender

app = Flask(__name__) #创建一个Flask应用对象

#首页路由：展示可选歌曲
@app.route("/", methods=["GET"])
def index():
    songs_df = recommender.get_display_songs(max_per_genre=4) #每种风格选取最多4首歌曲展示
    songs = songs_df.to_dict(orient="records")
    error = request.args.get("error") 
    return render_template("index.html", songs=songs, error=error) #渲染模板

#推荐路由：接收表单+生成推荐
@app.route("/recommend", methods=["POST"])
def recommend_route():
    selected_titles = request.form.getlist("favorite_titles") #获取表单列表
    if not selected_titles:
        return redirect(url_for("index", error="请至少选择一首歌曲。"))

    try:
        recommendations_df = recommender.recommend_by_titles(selected_titles, top_k=10) #调用推荐逻辑
    except ValueError as exc:
        return redirect(url_for("index", error=str(exc)))

    #根据所选歌名获取完整的歌曲信息（包含歌名、歌手、风格）
    songs_df = recommender.get_all_songs()
    favorites_df = songs_df[songs_df["title"].isin(selected_titles)]

    favorites = favorites_df.to_dict(orient="records")             #展示用户首页选取的歌曲
    recommendations = recommendations_df.to_dict(orient="records") #根据推荐所得到的歌曲
    return render_template(
        "result.html",
        favorites=favorites,             
        recommendations=recommendations, 
    )


if __name__ == "__main__":
    app.run(debug=True)
