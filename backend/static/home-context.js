const sourceProject = new URLSearchParams(window.location.search).get("project");
const interest = document.querySelector("#contact-interest");
if (sourceProject && interest) interest.value = `Проект: ${sourceProject.slice(0, 100)}`;
