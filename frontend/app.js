const videoInput = document.getElementById("video");
const fileName = document.getElementById("file-name");
const generateButton = document.getElementById("generate");
const statusMessage = document.getElementById("status-message");
const results = document.getElementById("results");
const clipList = document.getElementById("clip-list");
const downloadAll = document.getElementById("download-all");
const youtubeInput = document.getElementById("youtube-url");

youtubeInput.addEventListener("input", () => {
    const url = youtubeInput.value.trim();
    const match = url.match(
        /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
    );

    if (match) {
    statusMessage.textContent = "YouTube link recognized! ✓";

    let preview = document.getElementById("youtube-preview");

    if (!preview) {
        preview = document.createElement("iframe");
        preview.id = "youtube-preview";
        preview.width = "100%";
        preview.height = "220";
        preview.allowFullscreen = true;
        preview.style.marginTop = "15px";
        youtubeInput.parentElement.appendChild(preview);
    }

    preview.src = "https://www.youtube.com/embed/" + match[1];
}else if (url) {
        statusMessage.textContent = "Please enter a valid YouTube link.";
    } else {
        statusMessage.textContent = "";
    }
});
videoInput.addEventListener("change", () => {
    const file = videoInput.files[0];
    fileName.textContent = file ? file.name : "No video selected";
});

generateButton.addEventListener("click", async () => {
    const file = videoInput.files[0];

    if (!file) {
    statusMessage.textContent = youtubeInput.value.trim()
        ? "YouTube preview works! To generate clips, upload the video file you own or have permission to edit."
        : "Please upload a video first.";
    return;
}

    const formData = new FormData();
    formData.append("file", file);
    formData.append("clip_length", document.getElementById("length").value);
    formData.append("clip_count", document.getElementById("count").value);

    generateButton.disabled = true;
    generateButton.textContent = "⏳ Creating your clips...";
    statusMessage.textContent = "Uploading video and analyzing moments. This may take a while.";
    results.hidden = true;
    clipList.innerHTML = "";

    try {
        const response = await fetch("/api/process", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Something went wrong.");
        }

        data.clips.forEach((clip) => {
            const card = document.createElement("div");
            card.className = "clip";

            const title = document.createElement("strong");
            title.textContent = clip.name;

            const player = document.createElement("video");
            player.controls = true;
            player.playsInline = true;
            player.src = clip.url;

            const caption = document.createElement("p");
            caption.textContent = clip.text;

            const download = document.createElement("a");
            download.href = clip.url;
            download.download = clip.name + ".mp4";
            download.textContent = "Download clip ↓";

            card.append(title, player, caption, download);
            clipList.appendChild(card);
        });

        downloadAll.href = data.zip_url;
        results.hidden = false;
        statusMessage.textContent = "Your clips are ready! 🎉";

    } catch (error) {
        statusMessage.textContent = "Error: " + error.message;
    } finally {
        generateButton.disabled = false;
        generateButton.textContent = "✦ Generate my clips";
    }
});
youtubeInput.addEventListener("change", () => {
    const match = youtubeInput.value.match(
        /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
    );

    if (!match) return;

    let preview = document.getElementById("youtube-preview");

    if (!preview) {
        preview = document.createElement("iframe");
        preview.id = "youtube-preview";
        preview.width = "100%";
        preview.height = "220";
        preview.allowFullscreen = true;
        preview.style.marginTop = "15px";
        youtubeInput.parentElement.appendChild(preview);
    }

    preview.src = "https://www.youtube.com/embed/" + match[1];
});