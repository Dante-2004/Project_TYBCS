// JavaScript for home page functionality

document.getElementById("searchForm").addEventListener("submit", async function(event) {
  event.preventDefault();
  const query = document.getElementById("movieInput").value.trim();
  const resultsContainer = document.getElementById("resultsContainer");

  if (!query) {
    alert("Please enter a movie name.");
    return;
  }

  try {
    const response = await fetch("/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ movie: query })
    });

    if (!response.ok) {
      throw new Error("Failed to fetch recommendations.");
    }

    const data = await response.json();
    console.log(data);
    resultsContainer.innerHTML = "";

    if (data.recommendations && data.recommendations.length > 0) {
      data.recommendations.forEach((movie) => {
        const movieCard = document.createElement("div");
        movieCard.className = "carousel-item";
        movieCard.onclick = function() {
          showOverview(movie.title, movie.overview, movie.image_url);
        };

        const img = document.createElement("img");
        img.src = movie.image_url;
        img.alt = movie.title;

        const title = document.createElement("h3");
        title.textContent = movie.title;

        movieCard.appendChild(img);
        movieCard.appendChild(title);
        resultsContainer.appendChild(movieCard);
      });
    } else {
      resultsContainer.innerHTML = "<p>No recommendations found.</p>";
    }
  } catch (error) {
    console.error(error);
    resultsContainer.innerHTML = "<p>Error fetching recommendations. Please try again.</p>";
  }
});

function showOverview(title, content, imageUrl) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalContent").textContent = content;
  document.getElementById("modalImage").src = imageUrl;
  document.getElementById("overviewModal").style.display = "flex";
}

function closeModal() {
  document.getElementById("overviewModal").style.display = "none";
}

// Drag functionality for the results container
let isMouseDown = false;
let startX;
let scrollLeft;
const resultsContainer = document.getElementById("resultsContainer");

resultsContainer.addEventListener("mousedown", (e) => {
  isMouseDown = true;
  startX = e.pageX - resultsContainer.offsetLeft;
  scrollLeft = resultsContainer.scrollLeft;
  resultsContainer.style.cursor = "grabbing";
});

resultsContainer.addEventListener("mouseup", () => {
  isMouseDown = false;
  resultsContainer.style.cursor = "grab";
});

resultsContainer.addEventListener("mousemove", (e) => {
  if (!isMouseDown) return;
  e.preventDefault();
  const x = e.pageX - resultsContainer.offsetLeft;
  const walk = (x - startX) * 2;
  resultsContainer.scrollLeft = scrollLeft - walk;
});

resultsContainer.addEventListener("mouseleave", () => {
  isMouseDown = false;
});
