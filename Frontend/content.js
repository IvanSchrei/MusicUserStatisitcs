const spotifyConnectButton = document.getElementById("spotifyConnectButton");
const wrapButton = document.getElementById("getWrappedButton");
const logOutButton = document.getElementById("logoutButton");
const statusDiv = document.getElementById("status-message");
const trackList = document.getElementById("track-list");

document.addEventListener("DOMContentLoaded", () => {
    //checken, ob wir von Spotify Auth returnen
    handleSpotifyCallback();

    if (spotifyConnectButton) {
        spotifyConnectButton.addEventListener('click', async () => {
            updateStatus("Redirecting to Spotify...", "neutral");
            handleSpotifyLogin();
        });
    }

    if (wrapButton) {
        wrapButton.addEventListener('click', () => {
            getWrapped();
        });
    }

    if (logOutButton) {
        logOutButton.addEventListener('click', () => {
            logout();
        });
    }
});

//Axios setup
const api = axios.create({
    baseURL: 'https://musicuserstatisitcs.onrender.com',
    headers: {
        'Content-Type': 'application/json'
    }
});

//Token zu request headers hinzufügen
api.interceptors.request.use(
    (config) => {
        const token = sessionStorage.getItem("jwt_token");
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

//401 antworten behandeln
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            if(error.response.data && error.response.data.message === "Token has expired!"){
                logout();
            }
        }
        return Promise.reject(error);
    }
);

//Spotify Login
async function handleSpotifyLogin() {
    try {
        const response = await api.get('/api/spotify/link');

        if (response.status === 200) {
            window.location.href = response.data.url;
        } else {
            updateStatus("Could not fetch Spotify URL.", "error");
        }
    } catch (error) {
        console.error("Error getting Spotify URL: ", error);
        updateStatus("Failed to connect to server.", "error");
    }
}

//Wrapped Data von Backend holen
async function getWrapped() {
    trackList.innerHTML = "";
    updateStatus("Fetching your top songs...", "neutral");

    try {
        const response = await api.get('api/get-wrapped');

        if (response && response.data && response.data.data) {
            updateStatus("Here are your Top 5!", "success");
            renderTracks(response.data.data.items);
        } else {
            updateStatus("No data received.", "error");
        }
    } catch (error) {
        console.error("Error fetching wrapped: ", error);

        if (error.response) {
            if (error.response.status === 403) {
                updateStatus("Please link your Spotify account first (Button 1).", "error");
            } else if (error.response.status === 500) {
                //Dieser Fehler wird geworfen wenn Benutzer nicht unter allowed Users im Spotify Developer Dashboard ist
                updateStatus("Error: You are likely not added to the Developer Allowlist.", "error");
            } else {
                updateStatus(`Error: ${error.response.data.error || "Unknown Error"}`, "error");
            }
        } else {
            updateStatus("Network error. Is the server running?", "error");
        }
    }
}

//Top Songs Anzeigen
function renderTracks(items) {
    if (!items || items.length === 0) {
        trackList.innerHTML = "<li>No tracks found. Go listen to some music!</li>";
        return;
    }

    items.forEach((track, index) => {
        const li = document.createElement('li');
        li.className = 'track-item';

        const trackName = track.name;
        const artistName = track.artists.map(a => a.name).join(', ');
        //Bild holen
        const imageUrl = track.album.images[2]?.url || track.album.images[0]?.url || ''; 
        const spotifyUrl = track.external_urls.spotify;

        li.innerHTML = `
            <span class="rank">${index + 1}</span>
            <img src="${imageUrl}" alt="${trackName}" class="album-art">
            <div class="track-info">
                <a href="${spotifyUrl}" target="_blank" class="track-name">${trackName}</a>
                <div class="artist-name">${artistName}</div>
            </div>
        `;

        trackList.appendChild(li);
    });
}

//Status Text setzen
function updateStatus(message, type) {
    statusDiv.innerText = message;
    statusDiv.className = type === "error" ? "error-text" : (type === "success" ? "success-text" : "");
}

function logout() {
    sessionStorage.removeItem("jwt_token");
    window.location.href = "login.html";
}

async function handleSpotifyCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const auth_code = urlParams.get('code');

    if (auth_code) {
        updateStatus("Linking Spotify...", "neutral");
        //code von url entfernen, für besseres aussehen
        window.history.replaceState({}, document.title, window.location.pathname);

        try {
            const response = await api.post("/api/callback", { code: auth_code });
            if (response.status === 200) {
                updateStatus("Spotify Linked! Now click 'Get Top 5'.", "success");
            } else {
                updateStatus("Failed to link Spotify.", "error");
            }
        } catch (error) {
            console.log("Network error: ", error);
            updateStatus("Error linking account.", "error");
        }
    }
}