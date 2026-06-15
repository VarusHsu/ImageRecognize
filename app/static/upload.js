const form = document.querySelector("#upload-form");
const input = document.querySelector("#image-input");
const dropZone = document.querySelector(".drop-zone");
const preview = document.querySelector("#preview");
const emptyPreview = document.querySelector("#empty-preview");
const uploadButton = document.querySelector("#upload-button");
const statusBox = document.querySelector("#status");
const resultFilename = document.querySelector("#result-filename");
const resultKey = document.querySelector("#result-key");
const resultExpiry = document.querySelector("#result-expiry");
const resultLabel = document.querySelector("#result-label");
const resultConfidence = document.querySelector("#result-confidence");
const resultRecordId = document.querySelector("#result-record-id");
const predictionList = document.querySelector("#prediction-list");
const predictionEmpty = document.querySelector("#prediction-empty");

let selectedFile = null;
let previewUrl = null;

function setStatus(message, kind = "") {
  statusBox.textContent = message;
  statusBox.className = `status ${kind}`.trim();
}

function setFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    selectedFile = null;
    uploadButton.disabled = true;
    setStatus("请选择图片文件", "is-error");
    return;
  }

  selectedFile = file;
  uploadButton.disabled = false;
  resultFilename.textContent = file.name;
  resultKey.textContent = "-";
  resultExpiry.textContent = "-";
  resultLabel.textContent = "-";
  resultConfidence.textContent = "-";
  resultRecordId.textContent = "-";
  predictionList.replaceChildren();
  predictionEmpty.hidden = false;
  setStatus("图片已选择，准备上传");

  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
  }
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  preview.alt = file.name;
  preview.classList.add("has-image");
  emptyPreview.hidden = true;
}

async function requestPresignedUrl(file) {
  const response = await fetch("/uploads/presigned-url", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "生成上传地址失败");
  }
  return payload;
}

async function uploadToS3(file, presignedUpload) {
  const response = await fetch(presignedUpload.upload_url, {
    method: presignedUpload.method || "PUT",
    headers: presignedUpload.headers || {},
    body: file,
  });

  if (!response.ok) {
    throw new Error("上传到 S3 失败");
  }
}

async function recognizeImage(file, presignedUpload) {
  const response = await fetch("/recognize", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      bucket: presignedUpload.bucket,
      key: presignedUpload.key,
      filename: file.name,
      content_type: file.type,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "识别失败");
  }
  return payload;
}

function renderRecognition(record) {
  resultLabel.textContent = record.top_label || "-";
  resultConfidence.textContent = record.top_confidence == null
    ? "-"
    : `${(record.top_confidence * 100).toFixed(2)}%`;
  resultRecordId.textContent = record.id || "-";
  predictionList.replaceChildren();
  predictionEmpty.hidden = true;

  for (const prediction of (record.predictions || []).slice(0, 5)) {
    const item = document.createElement("li");
    const label = document.createElement("span");
    const confidenceText = document.createElement("strong");
    const confidence = (prediction.confidence * 100).toFixed(2);
    label.textContent = prediction.label;
    confidenceText.textContent = `${confidence}%`;
    item.append(label, confidenceText);
    predictionList.appendChild(item);
  }

  if (!predictionList.children.length) {
    predictionEmpty.hidden = false;
  }
}

input.addEventListener("change", () => {
  setFile(input.files[0]);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragging");
  setFile(event.dataTransfer.files[0]);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedFile) {
    setStatus("请选择图片文件", "is-error");
    return;
  }

  uploadButton.disabled = true;
  setStatus("正在生成 S3 上传地址...");

  try {
    const presignedUpload = await requestPresignedUrl(selectedFile);
    setStatus("正在上传到 S3...");
    await uploadToS3(selectedFile, presignedUpload);
    resultKey.textContent = presignedUpload.key;
    resultExpiry.textContent = `${presignedUpload.expires_in} 秒`;
    setStatus("上传完成，正在识别...");
    const recognition = await recognizeImage(selectedFile, presignedUpload);
    renderRecognition(recognition);
    setStatus("识别完成，记录已入库", "is-success");
  } catch (error) {
    setStatus(error.message, "is-error");
  } finally {
    uploadButton.disabled = false;
  }
});
