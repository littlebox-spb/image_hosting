document.addEventListener("DOMContentLoaded", () => {
  const heroPage = document.getElementById("hero-page");
  const mainAppPage = document.getElementById("main-app-page");
  const gotoAppButton = document.getElementById("goto-app-button");
  const navButtons = document.querySelectorAll(".app-nav__button");
  const uploadView = document.getElementById("upload-view");
  const imagesView = document.getElementById("images-view");
  const dropZone = document.getElementById("upload-drop-zone");
  const fileInput = document.getElementById("file-input");
  const browseBtn = document.getElementById("browse-btn");
  const uploadError = document.getElementById("upload-error");
  const urlInput = document.getElementById("url-input");
  const copyBtn = document.getElementById("copy-btn");
  const imageList = document.getElementById("image-list");
  const imageItemTemplate = document.getElementById("image-item-template");

  const heroImages = [
    "./assets/images/bird.jpg",
    "./assets/images/cat.jpg",
    "./assets/images/dog1.jpg",
    "./assets/images/dog2.jpg",
    "./assets/images/dog3.jpg",
  ];
  let uploadedImages = [];

  function setRandomHeroImage() {
    const randomIndex = Math.floor(Math.random() * heroImages.length);
    const randomImage = heroImages[randomIndex];
    heroPage.style.backgroundImage = `url(${randomImage})`;
  }

  gotoAppButton.addEventListener("click", () => {
    heroPage.classList.add("hidden");
    mainAppPage.classList.remove("hidden");
  });

  navButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const view = button.getAttribute("data-view");
      navButtons.forEach((btn) => {
        btn.classList.remove("active");
      });
      button.classList.add("active");
      if (view === "upload") {
        uploadView.classList.remove("hidden");
        imagesView.classList.add("hidden");
      } else {
        uploadView.classList.add("hidden");
        imagesView.classList.remove("hidden");
        renderImages();
      }
    });
  });

  function loadImagesFromLocalStorage() {
    const storedImages = localStorage.getItem("uploadedImages");
    if (storedImages) {
      try {
        uploadedImages = JSON.parse(storedImages);
        renderImages();
      } catch (error) {
        console.error("Error loading images from local storage:", error);
        uploadedImages = [];
      }
    }
  }

  function saveImagesToLocalStorage() {
    localStorage.setItem("uploadedImages", JSON.stringify(uploadedImages));
  }

  function handleFileUpload(file) {
    urlInput.value = '';
    uploadError.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            urlInput.value = data.url;
            uploadedImages.push({ id: Date.now(), name: file.name, url: data.url });
            saveImagesToLocalStorage();
            if (imagesView.classList.contains('hidden')) {
            } else {
                renderImages();
            }
        } else {
            uploadError.textContent = data.message;
            uploadError.classList.remove('hidden');
        }
    })
    .catch(error => {
        console.error('Upload failed:', error);
        uploadError.textContent = 'Upload failed due to network error.';
        uploadError.classList.remove('hidden');
    });
}

  browseBtn.addEventListener("click", () => {
    fileInput.click();
  });

  dropZone.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  copyBtn.addEventListener("click", () => {
    if (urlInput.value) {
      navigator.clipboard.writeText(urlInput.value).then(() => {
        copyBtn.textContent = "Copied!";
        setTimeout(() => {
          copyBtn.textContent = "Copy";
        }, 2000);
      });
    }
  });

  function renderImages() {
    imageList.innerHTML = "";
    if (uploadedImages.length === 0) {
      imageList.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 20px;" class="no-images">No images uploaded yet.</p>`;
      return;
    }
    uploadedImages.forEach((image) => {
      const templateClone = imageItemTemplate.content.cloneNode(true);
      templateClone.querySelector(".image-item").dataset.id = image.id;
      templateClone.querySelector(".image-item__name span").textContent =
        image.name;
      const urlLink = templateClone.querySelector(".image-item__url a");
      urlLink.href = image.url;
      urlLink.textContent = image.url;
      templateClone.querySelector(".image-item__url a").href = image.url;
      imageList.appendChild(templateClone);
    });
  }

  imageList.addEventListener("click", (e) => {
    const deleteButton = e.target.closest(".delete-btn");
    if (deleteButton) {
      const listItem = e.target.closest(".image-item");
      const imageId = parseInt(listItem.dataset.id, 10);
      uploadedImages = uploadedImages.filter((img) => img.id !== imageId);
      saveImagesToLocalStorage();
      renderImages();
    }
  });

  loadImagesFromLocalStorage();
  setRandomHeroImage();
});
