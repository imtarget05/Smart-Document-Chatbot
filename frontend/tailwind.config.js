module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      colors: {
        /* Google Brand Colors */
        google: {
          blue: "#1a73e8",
          blueDark: "#185abc",
          blueLight: "#4285f4",
          red: "#d93025",
          yellow: "#fbbc05",
          green: "#34a853",
        },
        /* Material Design Surface */
        surface: {
          DEFAULT: "#ffffff",
          dim: "#f8f9fa",
          bright: "#ffffff",
          container: "#f1f3f4",
          containerHigh: "#e8eaed",
        },
        /* Material Design On-Surface */
        onsurface: {
          DEFAULT: "#202124",
          variant: "#3c4043",
          muted: "#5f6368",
          disabled: "#9aa0a6",
        },
        /* Material Design Outline */
        outline: {
          DEFAULT: "#dadce0",
          variant: "#e8eaed",
        },
        /* Legacy primary/neutral (keep for backwards compat) */
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          500: "#1a73e8",
          600: "#185abc",
          700: "#0369a1",
        },
        neutral: {
          50: "#fafafa",
          100: "#f5f5f5",
          200: "#e5e5e5",
          300: "#d4d4d4",
          400: "#a3a3a3",
          500: "#737373",
          600: "#525252",
          700: "#404040",
          800: "#262626",
          900: "#171717",
        },
      },
      fontFamily: {
        sans: ["Google Sans", "Roboto", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        roboto: ["Roboto", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
      /* Material Design Elevation */
      boxShadow: {
        "material-1": "0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15)",
        "material-2": "0 1px 2px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15)",
        "material-3": "0 4px 8px 3px rgba(60,64,67,0.15), 0 1px 3px 0 rgba(60,64,67,0.3)",
        "material-4": "0 6px 10px 4px rgba(60,64,67,0.15), 0 2px 3px 0 rgba(60,64,67,0.3)",
        "material-btn": "0 1px 2px rgba(60,64,67,0.3), 0 1px 3px rgba(60,64,67,0.15)",
        "material-btn-hover": "0 1px 3px rgba(60,64,67,0.3), 0 4px 8px rgba(60,64,67,0.15)",
      },
      /* Material Design Border Radius */
      borderRadius: {
        "material": "8px",
        "material-lg": "12px",
        "material-xl": "16px",
        "material-2xl": "24px",
        "material-full": "9999px",
      },
      /* Material Design Motion */
      transitionDuration: {
        "200": "200ms",
        "300": "300ms",
        "400": "400ms",
      },
      transitionTimingFunction: {
        "material": "cubic-bezier(0.4, 0, 0.2, 1)",
        "material-decelerate": "cubic-bezier(0, 0, 0.2, 1)",
        "material-accelerate": "cubic-bezier(0.4, 0, 1, 1)",
      },
      keyframes: {
        ripple: {
          "0%": { transform: "scale(0)", opacity: "0.5" },
          "100%": { transform: "scale(4)", opacity: "0" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideInRight: {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
      },
      animation: {
        ripple: "ripple 600ms cubic-bezier(0.4, 0, 0.2, 1)",
        "fade-in": "fadeIn 200ms cubic-bezier(0.4, 0, 0.2, 1)",
        "slide-up": "slideUp 300ms cubic-bezier(0.4, 0, 0.2, 1)",
        "slide-in-right": "slideInRight 300ms cubic-bezier(0.4, 0, 0.2, 1)",
      },
      spacing: {
        "sidebar": "280px",
        "appbar": "56px",
      },
    },
  },
  plugins: [],
}
