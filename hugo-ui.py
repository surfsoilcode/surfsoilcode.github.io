from flask import Flask, request, render_template_string, redirect, url_for, flash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret"

CONTENT_DIR = "content/posts"
STATIC_IMG_DIR = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

for d in [CONTENT_DIR, STATIC_IMG_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

TEMPLATE = """
<!doctype html>
<title>Daily Thoughts with Live Preview</title>
<style>
  #preview img {
    max-width: 100px;
    height: auto;
    display: block;
    margin: 12px auto;
  }
</style>
<h2>Thoughts for {{ date }}</h2>

<div style="display:flex; flex-direction:column; gap: 20px;">

  <form method="POST" action="{{ url_for('upload_image') }}" enctype="multipart/form-data" style="margin-bottom:12px;">
      <h3>Upload an Image</h3>
      <input type="file" name="image" accept="image/*" required>
      <button type="submit">Upload Image</button>
  </form>

  <form method="POST" action="{{ url_for('daily_thoughts') }}">
      <textarea id="editor" name="thoughts" rows="20" style="width:100%;">{{ content }}</textarea><br>
      <button type="submit">Save</button>
  </form>

  <div style="border: 1px solid #ccc; padding: 10px; overflow-y:auto; max-height:500px;">
      <h3>Live Preview</h3>
      <div id="preview"></div>
  </div>
</div>

{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color: red;">
      {% for msg in messages %}
        <li>{{ msg }}</li>
      {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
  const editor = document.getElementById('editor');
  const preview = document.getElementById('preview');

  function updatePreview() {
    const markdownText = editor.value;
    preview.innerHTML = marked.parse(markdownText);
  }

  editor.addEventListener('input', updatePreview);

  // Initialize preview on page load
  updatePreview();
</script>
"""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_markdown_path(date_str):
    return os.path.join(CONTENT_DIR, f"{date_str}.md")

def get_image_folder(date_str):
    path = os.path.join(STATIC_IMG_DIR, date_str)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def load_content(filepath):
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    try:
        first_delim = lines.index("---\n")
        second_delim = lines.index("---\n", first_delim + 1)
        body = lines[second_delim + 1:]
    except ValueError:
        body = lines
    return "".join(body).strip()

def save_content(filepath, date_str, new_text):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f'title: "{date_str}"\n')
        f.write(f"date: {date_str}\n")
        f.write('tags: ["Blog"]\n')
        f.write("---\n\n")
        f.write(new_text.strip())

@app.route("/", methods=["GET", "POST"])
def daily_thoughts():
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = get_markdown_path(date_str)

    if request.method == "POST":
        thoughts = request.form.get("thoughts", "").strip()
        if thoughts:
            save_content(filepath, date_str, thoughts)
        return redirect(url_for("daily_thoughts"))

    content = load_content(filepath)
    #content_for_preview = content.replace("](/images/", "](/static/images/")
    return render_template_string(TEMPLATE, date=date_str, content=content)

from flask import send_from_directory

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/images'), filename)

@app.route("/upload-image", methods=["POST"])
def upload_image():
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = get_markdown_path(date_str)
    image_folder = get_image_folder(date_str)

    if 'image' not in request.files:
        flash("No image file part")
        return redirect(url_for("daily_thoughts"))
    file = request.files['image']
    if file.filename == '':
        flash("No selected file")
        return redirect(url_for("daily_thoughts"))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(image_folder, filename)

        if os.path.exists(save_path):
            # File exists, do NOT overwrite; just reuse filename
            flash(f"Image '{filename}' already exists, using existing file.")
        else:
            # Save the file since it doesn't exist yet
            file.save(save_path)
            flash(f"Image '{filename}' uploaded and added to your thoughts.")

        content = load_content(filepath)
        image_markdown = f'![{filename}](/images/{date_str}/{filename})'

        # Avoid duplicate markdown lines for the same image
        if image_markdown not in content:
            if content:
                content += f"\n\n{image_markdown}\n"
            else:
                content = image_markdown
            save_content(filepath, date_str, content)
        else:
            flash(f"Image '{filename}' already referenced in your thoughts.")

        return redirect(url_for("daily_thoughts"))
    else:
        flash("Unsupported file type. Allowed: png, jpg, jpeg, gif.")
        return redirect(url_for("daily_thoughts"))


if __name__ == "__main__":
    app.run(debug=True)
