const spotifyConnectButton = document.getElementById("spotifyConnectButton")
const wrapButton = document.getElementById("getWrappedButton")
const logOutButton = document.getElementById("logoutButton")

document.addEventListener("DOMContentLoaded", ()=>{
    //on first load this should return an error, but after returning from spotify login it should send the code to backend
    handleSpotifyCallback(); 

    if(spotifyConnectButton){
        spotifyConnectButton.addEventListener('click', async ()=>{
            console.log("log into spotify");
            handleSpotifyLogin()
        });
    }

    if(wrapButton){
        wrapButton.addEventListener('click', ()=>{
            console.log("get wrapped");
            getWrapped();
        });
    }

    if(logOutButton){
        logOutButton.addEventListener('click', ()=>{
            console.log("logging out")
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

//Axios Request Interceptor erstellen, spielt den "Mittelmann",
//wird vor jedem request ausgeführt, checkt ob token in browser ist und wenn ja gibt in in den Header
api.interceptors.request.use(
    (config) => {
        const token = sessionStorage.getItem("jwt_token");
        if(token){
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config
    },
    (error) => {
        return Promise.reject(error);
    }
);

//Axios Response Interceptor
//bei jeder api response wird geschaut ob es ein 401(Unauthorized) war,
//und wenn ja wird ausgeloggt
api.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if(error.response && error.response.status === 401){
            logout();
        }
    }
)

//Methode, um Spotify Login über OAuth2 auszuführen
async function handleSpotifyLogin(){
    try{
        const response = await api.get('/api/spotify/link');
        
        if(response.status === 200){
            console.log("Erfolgreich Spotify Url geholt!");
            window.location.href = response.data.url;
        }
        else{
            console.log("Spotify Url konnte nicht geholt werden")
        }
    }
    catch(error){
        console.log("Error beim Holen der Spotify Url: ", error)
    }
}

async function getWrapped(){
    try{
        const response = await api.get('api/get-wrapped');
        console.log("response: ", response)
        if(response){
            console.log("wrapped stats: ", response.data);
        }
        else{
            console.log("response undefined")
        }
    }
    catch(error){
        console.error("Error beim holen von Wrapped: ", error)
    }
}

function logout(){
    sessionStorage.removeItem("jwt_token");
    window.location.href = "login.html";
}

async function handleSpotifyCallback(){
    const urlParams = new URLSearchParams(window.location.search);
    const auth_code = urlParams.get('code');
    if(auth_code){
        try{
            const response = await api.post("https://musicuserstatisitcs.onrender.com/api/callback", {code: auth_code});
            if(response.status == 200){
                console.log("Callback code handled")
                window.history.replaceState({}, document.title, window.location.pathname);
            }
            else{
                console.log("Error handling callback code")
            }
        }
        catch(error){
            console.log("Network error: ", error)
        }
    }
}