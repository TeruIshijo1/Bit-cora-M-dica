/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        'hes-blue-main': '#004687',
        'hes-blue-light': '#006bbd',
        'hes-blue-cross': '#002b5e',
        'hes-green': '#00974a',
      }
    },
  },
  plugins: [],
}
