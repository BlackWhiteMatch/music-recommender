from flask import Flask, render_template, request, redirect, url_for

import recommender

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    songs_df = recommender.get_all_songs()
    songs = songs_df.to_dict(orient="records")
    error = request.args.get("error")
    return render_template("index.html", songs=songs, error=error)


@app.route("/recommend", methods=["POST"])
def recommend_route():
    selected_titles = request.form.getlist("favorite_titles")
    if not selected_titles:
        return redirect(url_for("index", error="请至少选择一首歌曲。"))

    try:
        recommendations_df = recommender.recommend_by_titles(selected_titles, top_k=10)
    except ValueError as exc:
        return redirect(url_for("index", error=str(exc)))

    recommendations = recommendations_df.to_dict(orient="records")
    return render_template(
        "result.html",
        favorites=selected_titles,
        recommendations=recommendations,
    )


if __name__ == "__main__":
    app.run(debug=True)
