/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        razorpay: {
          blue: "#0c2340",
          accent: "#3395ff",
          dark: "#0b1426",
          card: "#131f37",
          border: "#1e2f4d",
          success: "#10b981",
          warning: "#f59e0b",
          danger: "#ef4444"
        }
      }
    },
  },
  plugins: [],
}
