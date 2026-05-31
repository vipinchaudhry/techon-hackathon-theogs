import "./globals.css";
import { Sidebar } from "../components/sidebar";

export const metadata = {
  title: "Uncertainty Navigator",
  description: "Decisions driven by what you can afford to lose.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <Sidebar />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
