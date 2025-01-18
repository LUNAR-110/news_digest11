// Format date and time
function formatDateTime(date, time) {
    if (date === "N/A" && time === "N/A") return "Publication date unavailable";
    if (time === "N/A") return date;
    return `${date} at ${time}`;
}

// Fetch articles dynamically from all sources
async function fetchAllArticles() {
    try {
        const endpoints = [
            "/fetch-hindu-news",
            "/fetch-mint-news",
            "/fetch-financial-news",
            "/fetch-news18-news",
          
        ];

        const articlesContainer = document.getElementById("articles");
        articlesContainer.innerHTML = ""; // Clear previous content

        for (const endpoint of endpoints) {
            const response = await fetch(endpoint);
            const articles = await response.json();

            if (articles.error) {
                articlesContainer.innerHTML += `<p>${articles.error}</p>`;
                continue;
            }

            articlesContainer.innerHTML += articles.map(article => `
                <div class="card">
                    <h3>${article.headline}</h3>
                    <p>${article.summary}</p>
                    <div class="metadata">
                        <span class="source">Source: ${article.source}</span>
                    </div>
                    <a href="${article.url}" target="_blank">Read More</a>
                </div>
            `).join("");
        }
    } catch (error) {
        console.error("Error fetching articles:", error);
    }
}

// Initial fetch for all articles
fetchAllArticles();
