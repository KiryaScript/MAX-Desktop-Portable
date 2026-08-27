const { ipcRenderer } = require("electron");

(function() {
  // In-guest window.open hook to keep file downloads inside the app
  try {
    const origWindowOpen = window.open;
    window.open = function(url, target, features) {
      if (url && typeof url === "string") {
        const isDownload =
          url.startsWith("blob:") ||
          url.startsWith("data:") ||
          url.includes("max.ru") ||
          url.includes("storage") ||
          url.includes("download") ||
          url.includes("file") ||
          url.includes("attachment") ||
          url.includes("media") ||
          url.includes("selcloud") ||
          url.includes("selcdn") ||
          url.includes("bizmrg") ||
          /\.(jpg|jpeg|png|gif|webp|svg|ico|bmp|mp4|webm|mov|avi|mkv|mp3|ogg|wav|m4a|aac|flac|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z|tar|gz|apk|exe|msi|txt|csv|json|xml|bin|dat|iso)(\?.*)?$/i.test(url);

        if (isDownload) {
          try {
            const a = document.createElement("a");
            a.href = url;
            a.download = "";
            (document.body || document.documentElement).appendChild(a);
            a.click();
            setTimeout(() => a.remove(), 100);
            return null;
          } catch(e) {}
        }
      }
      return origWindowOpen.call(this, url, target, features);
    };
  } catch(e) {}

  ipcRenderer.on("apply-stealth-config", (event, config) => {
    try {
      if (!config) return;

      const mask = config.maskData;
      if (mask) {
        const defineProp = (obj, prop, value) => {
          try {
            Object.defineProperty(obj, prop, {
              get: () => value,
              configurable: true,
              enumerable: true
            });
          } catch(e) {}
        };

        defineProp(navigator, "userAgent", mask.ua);
        defineProp(navigator, "appVersion", mask.ua.replace(/^Mozilla\//, ""));
        defineProp(navigator, "platform", mask.platform);
        defineProp(navigator, "vendor", mask.vendor);
        defineProp(navigator, "hardwareConcurrency", 8);
        defineProp(navigator, "deviceMemory", 8);
        defineProp(navigator, "languages", ["ru-RU", "ru", "en-US", "en"]);
        defineProp(navigator, "language", "ru-RU");
        defineProp(navigator, "webdriver", false);
        defineProp(navigator, "maxTouchPoints", mask.touch || 0);
      }

      // WebRTC Leak Protection Hook
      if (config.webrtc_leak) {
        try {
          const OrigRTC = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
          if (OrigRTC) {
            const ProtectedRTC = function(rtcConfig, constraints) {
              const safeConfig = rtcConfig ? { ...rtcConfig } : {};
              safeConfig.iceTransportPolicy = "relay";
              return new OrigRTC(safeConfig, constraints);
            };
            ProtectedRTC.prototype = OrigRTC.prototype;
            window.RTCPeerConnection = ProtectedRTC;
            if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = ProtectedRTC;
            if (window.mozRTCPeerConnection) window.mozRTCPeerConnection = ProtectedRTC;
          }
        } catch(e) {}
      }

      // Canvas Noise
      if (config.canvas_noise !== false) {
        try {
          const origTDU = HTMLCanvasElement.prototype.toDataURL;
          HTMLCanvasElement.prototype.toDataURL = function(type) {
            try {
              const ctx = this.getContext("2d");
              if (ctx && (!type || type.includes("image/png") || type.includes("image/jpeg"))) {
                const prev = ctx.fillStyle;
                ctx.fillStyle = "rgba(255,255,255,0.01)";
                ctx.fillRect(0, 0, 1, 1);
                ctx.fillStyle = prev;
              }
            } catch (e) {}
            return origTDU.apply(this, arguments);
          };
        } catch(e) {}
      }

      // Audio Noise
      if (config.audio_noise !== false) {
        try {
          if (window.AudioBuffer) {
            const origGCD = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function(channel) {
              const data = origGCD.call(this, channel);
              try {
                if (data && data.length > 0) {
                  for (let i = 0; i < Math.min(64, data.length); i++) {
                    const idx = Math.floor(Math.random() * data.length);
                    data[idx] += (Math.random() * 0.0001 - 0.00005);
                  }
                }
              } catch (e) {}
              return data;
            };
          }
        } catch(e) {}
      }

      // CSS Themes & Injections
      const injectCss = () => {
        try {
          if (!document.head) return;
          let el = document.getElementById("max-stealth-injected-style");
          if (!el) {
            el = document.createElement("style");
            el.id = "max-stealth-injected-style";
            document.head.appendChild(el);
          }
          el.textContent = config.css || "";
        } catch(e) {}
      };

      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectCss);
      } else {
        injectCss();
      }

    } catch(err) {
      console.warn("Stealth preload error:", err);
    }
  });

  ipcRenderer.sendToHost("stealth-ready");
})();
