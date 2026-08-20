import type { MetadataRoute } from "next";

/**
 * Lets a manager keep VMF on their home screen.
 *
 * Nearly all of this league is read on a phone, on a Saturday, between
 * kick-offs. Installed, the site opens straight onto the scores with no
 * browser chrome in the way, which is the whole interaction.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "VMF League · Văn Minh Fantasy",
    short_name: "VMF League",
    description: "Fixtures, live head-to-head scores and Cup brackets for VMF Fantasy League.",
    start_url: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#0a1020",
    theme_color: "#0a1020",
    categories: ["sports"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      // Android crops an installed icon to whatever shape the launcher uses,
      // so the maskable copy carries extra margin around the mark.
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
    ]
  };
}
