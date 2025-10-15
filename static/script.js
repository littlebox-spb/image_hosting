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

  /*
   * Sets a random hero image from the heroImages array.
   *
   * @function setRandomHeroImage
   * @return {void}
   */

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

  /**
   * Handles a file upload event by sending the file to the server
   * and populating the URL input field with the uploaded image's URL.
   *
   * @param {File} file - The file to be uploaded.
   */
  function handleFileUpload(file) {
    urlInput.value = "";
    uploadError.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", file);

    fetch("/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          urlInput.value = data.url;
          uploadedImages.push({
            id: Date.now(),
            name: file.name,
            url: data.url,
          });
          if (imagesView.classList.contains("hidden")) {
          } else {
            renderImages();
          }
        } else {
          uploadError.textContent = data.message;
          uploadError.classList.remove("hidden");
        }
      })
      .catch((error) => {
        console.error("Upload failed:", error);
        uploadError.textContent = "Upload failed due to network error.";
        uploadError.classList.remove("hidden");
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

  let current_page = 1;

  /**
   * Renders a list of uploaded images
   * @param {number} page - The page number to render, defaults to 1
   * @throws {Error} If there is an error fetching the images
   */
  async function renderImages(page = 1) {
    try {
      const response = await fetch(`/images-list?page=${page}`);
      const data = await response.json();
      uploadedImages = data.images;
      imageList.innerHTML = "";
      const paginationContainer = document.getElementById("pagination");
      if (uploadedImages.length === 0) {
        imageList.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 20px;" class="no-images">No images uploaded yet.</p>`;
        paginationContainer.innerHTML = "";
        return;
      }
      uploadedImages.forEach((image) => {
        const templateClone = imageItemTemplate.content.cloneNode(true);
        templateClone.querySelector(".image-item").dataset.id = image.id;
        templateClone.querySelector(".image-item__name span").textContent =
          image.original_name;
        const urlLink = templateClone.querySelector(".image-item__url a");
        urlLink.href = `/images/${image.filename}`;
        urlLink.textContent = `/images/${image.filename}`;
        imageList.appendChild(templateClone);
      });
      if (paginationContainer) {
        paginationContainer.innerHTML = `
          <button id="prev-page" ${
            !data.pagination.has_prev ? "disabled" : ""
          }>Previous</button>
          <span>Page ${data.pagination.current_page} of ${
          data.pagination.total_pages
        }</span>
          <button id="next-page" ${
            !data.pagination.has_next ? "disabled" : ""
          }>Next</button>
        `;

        document.getElementById("prev-page").addEventListener("click", () => {
          if (current_page > 1) {
            current_page--;
            renderImages(current_page);
          }
        });

        document.getElementById("next-page").addEventListener("click", () => {
          if (data.pagination.has_next) {
            current_page++;
            renderImages(current_page);
          }
        });
      }
    } catch (error) {
      console.error("Error fetching images:", error);
      const paginationContainer = document.getElementById("pagination");
      if (paginationContainer) {
        paginationContainer.innerHTML = "";
      }
    }
  }

  imageList.addEventListener("click", async (e) => {
    const deleteButton = e.target.closest(".delete-btn");
    if (deleteButton) {
      const listItem = e.target.closest(".image-item");
      const imageId = parseInt(listItem.dataset.id, 10);
      if (confirm("Are you sure you want to delete this image?")) {
        try {
          const response = await fetch(`/delete/${imageId}`, {
            method: "DELETE",
          });
          if (response.ok) {
            renderImages();
          }
        } catch (error) {
          console.error("Error deleting image:", error);
        }
      }
    }
  });

  setRandomHeroImage();
});
