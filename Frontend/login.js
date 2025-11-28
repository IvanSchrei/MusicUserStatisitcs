const registerButton = document.getElementById("registerButton");
const loginForm = document.getElementById("loginForm")

document.addEventListener("DOMContentLoaded", ()=>{
    document.addEventListener("submit", async (event)=>{
        event.preventDefault();
        formData = new FormData(loginForm);

        const data = Object.fromEntries(formData.entries());
        
        handleLogin(data);
    });
    registerButton.addEventListener("click", ()=>{
        window.location.href="index.html";
    });
});

//Methode um Login des Users in unsere Webseite zu verwalten
async function handleLogin(data){
    try{
        const response = await fetch("https://musicuserstatisitcs.onrender.com/api/login", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if(response.ok){
            console.log("Erfolgreich eingeloggt!");
            const responseData = await response.json();
            const token = responseData.token.trim();
            sessionStorage.setItem("jwt_token", token)
            window.location.href = "content.html";
        }
        else{
            console.log("Login Fehlgeschlagen")
            //Add output for user to tell him that it failed, might be because he is not registered
        }
    }
    catch(error){
        console.log("Error bei Login: ", error)
    }
}