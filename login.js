const registrierenButton = document.getElementById("registrierenButton");
const loginForm = document.getElementById("loginForm")

document.addEventListener("DOMContentLoaded", ()=>{
    document.addEventListener("submit", async (event)=>{
        event.preventDefault();
        formData = new FormData(loginForm);

        const data = Object.fromEntries(formData.entries());
        
        handleLogin(data);
    })
});

//Methode um Login des Users in unsere Webseite zu verwalten
async function handleLogin(data){
    try{
        const response = await fetch("http://127.0.0.1:5000/api/login", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if(response.ok){
            console.log("Erfolgreich eingeloggt!");
            const responseData = await response.json();
            const token = responseData.token.trim();
            sessionStorage.setItem("jwt_token", token)
            await new Promise(r => setTimeout(r, 5000));
            window.location.href = "content.html";
        }
        else{
            console.log("Login Fehlgeschlagen")
        }
    }
    catch(error){
        console.log("Error bei Login: ", error)
    }
}