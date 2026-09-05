import { Moon, Sun } from "lucide-react";

function ThemeToggle({ theme, setTheme }) {
    const toggleTheme = () => {
        const newTheme = theme === "dark" ? "light" : "dark";

        setTheme(newTheme);
        localStorage.setItem("recoverx-theme", newTheme);
    };

    return (
        <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
            {theme === "dark" ? <Sun size={19} /> : <Moon size={19} />}
        </button>
    );
}

export default ThemeToggle;