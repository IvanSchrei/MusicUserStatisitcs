const spotifyConnectButton = document.getElementById("spotifyConnectButton")
const wrapButton = document.getElementById("getWrappedButton")

document.addEventListener("DOMContentLoaded", ()=>{
    spotifyConnectButton.addEventListener('click', async ()=>{
        console.log("log into spotify");
        handleSpotifyLogin()
    });
    wrapButton.addEventListener('click', ()=>{
        console.log("get wrapped");
        getWrapped()
    });
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
            sessionStorage.removeItem("jwt_token");
            window.location.href = "login.html"
        }
    }
)

//Methode, um Spotify Login über OAuth2 auszuführen
async function handleSpotifyLogin(){
    try{
        const response = await api.get('/api/spotify/link');
        
        if(response.ok){
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