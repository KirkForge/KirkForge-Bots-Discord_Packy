document.addEventListener("DOMContentLoaded", () => {
    const cmdInput = document.getElementById("cmd");
    const output = document.getElementById("output");

    const history = [];
    let historyIndex = -1;

    cmdInput.addEventListener("keydown", async (e) => {

        // =============== CTRL + L (Clear Screen) ===============
        if (e.ctrlKey && e.key === "l") {
            e.preventDefault();
            output.innerHTML = "";
            appendOutput("** Screen cleared **");
            return;
        }

        // =============== CTRL + C (Interrupt Command) ===============
        if (e.ctrlKey && e.key === "c") {
            e.preventDefault();
            appendOutput("^C");
            cmdInput.value = "";
            appendOutput("packy: \"Interrupted? Finally, some peace.\"");
            return;
        }

        // =============== CTRL + U (Clear entire line) ===============
        if (e.ctrlKey && e.key === "u") {
            e.preventDefault();
            cmdInput.value = "";
            return;
        }

        // =============== CTRL + K (Kill to end of line) ===============
        if (e.ctrlKey && e.key === "k") {
            e.preventDefault();
            const pos = cmdInput.selectionStart;
            cmdInput.value = cmdInput.value.substring(0, pos);
            return;
        }

        // =============== ARROW UP (command history) ===============
        if (e.key === "ArrowUp") {
            e.preventDefault();
            if (history.length === 0) return;

            if (historyIndex === -1) {
                historyIndex = history.length - 1;
            } else if (historyIndex > 0) {
                historyIndex--;
            }

            cmdInput.value = history[historyIndex];
            return;
        }

        // =============== ARROW DOWN (command history) ===============
        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (history.length === 0) return;

            historyIndex++;
            if (historyIndex >= history.length) {
                historyIndex = -1;
                cmdInput.value = "";
                return;
            }

            cmdInput.value = history[historyIndex];
            return;
        }

        // =============== ENTER (execute command) ===============
        if (e.key === "Enter") {
            const userCmd = cmdInput.value.trim();
            cmdInput.value = "";

            if (userCmd === "") return;

            history.push(userCmd);
            historyIndex = -1;

            appendOutput(`packy@lair:~$ ${userCmd}`);

            const response = await fetch("/api/packy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command: userCmd })
            });

            const data = await response.json();

            updateHUD(data.state);
            appendOutput(data.result);
        }
    });

    function appendOutput(text) {
        output.innerHTML += text + "\n";
        output.scrollTop = output.scrollHeight;
    }

    function updateHUD(state) {
        document.getElementById("cpu").innerText = `CPU: ${state.cpu_pct}%`;
        document.getElementById("weather").innerText = `Weather: ${state.weather}`;
        document.getElementById("mood").innerText = `Mood: ${state.mood}`;
    }
});
