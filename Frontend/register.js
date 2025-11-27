const loginButton = document.getElementById("loginButton");
const registerForm = document.getElementById("registrationForm")

document.addEventListener("DOMContentLoaded", ()=>{
    document.addEventListener("submit", async (event)=>{
        event.preventDefault();
        formData = new FormData(registerForm);

        const data = Object.fromEntries(formData.entries());
        
        handleRegistration(data);
    });
    loginButton.addEventListener("click", ()=>{
        window.location.href = "login.html"
    });
});

//Methode um Login des Users in unsere Webseite zu verwalten
async function handleRegistration(data){
    try{
        const response = await fetch("https://musicuserstatisitcs.onrender.com/api/register", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if(response.ok){
            console.log("Erfolgreich registriert!");
            window.location.href = "login.html";
        }
        else{
            console.log("Registration Fehlgeschlagen")
        }
    }
    catch(error){
        console.log("Error bei Registration: ", error)
    }
}