const { MASKS_DB, THEMES } = require("./constants");

function getStealthInjectionCode(profileConfig) {
  const mask = MASKS_DB[profileConfig.mask] || MASKS_DB["Windows 11 (Chrome)"];
  const canvasNoise = profileConfig.canvas_noise !== false;
  const audioNoise = profileConfig.audio_noise !== false;
  const webrtcStrict = Boolean(profileConfig.webrtc_leak);
  const hideScrollbars = Boolean(profileConfig.hide_scrollbars);
  const adblock = Boolean(profileConfig.adblock);
  const themeCss = THEMES[profileConfig.theme] || "";

  let fullCss = themeCss;
  if (hideScrollbars) {
    fullCss += "\n::-webkit-scrollbar { display: none !important; }";
  }
  if (adblock) {
    fullCss += `
      .ads, .advertisement, [id*='yandex_rtb'], .banner, [class*='adsbygoogle'], [id*='ad-container'] {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
      }
    `;
  }

  const maskJson = JSON.stringify(mask);
  const cssJson = JSON.stringify(fullCss);

  return `
  (function() {
    try {
      const config = ${maskJson};

      // 1. Spoof Navigator properties
      const defineProp = (obj, prop, value) => {
        try {
          Object.defineProperty(obj, prop, {
            get: () => value,
            configurable: true,
            enumerable: true
          });
        } catch(e) {}
      };

      defineProp(navigator, 'userAgent', config.ua);
      defineProp(navigator, 'appVersion', config.ua.replace(/^Mozilla\\//, ''));
      defineProp(navigator, 'platform', config.platform);
      defineProp(navigator, 'vendor', config.vendor);
      defineProp(navigator, 'hardwareConcurrency', 8);
      defineProp(navigator, 'deviceMemory', 8);
      defineProp(navigator, 'languages', ['ru-RU', 'ru', 'en-US', 'en']);
      defineProp(navigator, 'language', 'ru-RU');
      defineProp(navigator, 'webdriver', false);
      defineProp(navigator, 'maxTouchPoints', config.touch || 0);

      // Clean automation traces
      if (window.navigator.plugins && window.navigator.plugins.length === 0) {
        try {
          Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
          });
        } catch(e) {}
      }

      // 2. WebRTC Leak Protection
      if (${webrtcStrict}) {
        try {
          const OrigRTC = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
          if (OrigRTC) {
            const ProtectedRTC = function(rtcConfig, constraints) {
              const safeConfig = rtcConfig ? { ...rtcConfig } : {};
              safeConfig.iceTransportPolicy = 'relay';
              return new OrigRTC(safeConfig, constraints);
            };
            ProtectedRTC.prototype = OrigRTC.prototype;
            window.RTCPeerConnection = ProtectedRTC;
            if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = ProtectedRTC;
            if (window.mozRTCPeerConnection) window.mozRTCPeerConnection = ProtectedRTC;
          }
        } catch(e) {}
      }

      // 3. Canvas Noise Protection
      if (${canvasNoise}) {
        try {
          const origTDU = HTMLCanvasElement.prototype.toDataURL;
          HTMLCanvasElement.prototype.toDataURL = function(type) {
            try {
              const ctx = this.getContext('2d');
              if (ctx && (!type || type.includes('image/png') || type.includes('image/jpeg'))) {
                const prev = ctx.fillStyle;
                ctx.fillStyle = 'rgba(255,255,255,0.01)';
                ctx.fillRect(0, 0, 1, 1);
                ctx.fillStyle = prev;
              }
            } catch (e) {}
            return origTDU.apply(this, arguments);
          };

          const origGID = CanvasRenderingContext2D.prototype.getImageData;
          CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
            const res = origGID.apply(this, arguments);
            try {
              if (res && res.data && res.data.length > 4) {
                for (let i = 0; i < Math.min(16, res.data.length / 4); i++) {
                  const idx = (i * 4);
                  res.data[idx] = (res.data[idx] ^ 1);
                }
              }
            } catch(e) {}
            return res;
          };
        } catch (e) {}
      }

      // 4. AudioContext Noise Protection
      if (${audioNoise}) {
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
        } catch (e) {}
      }

      // 5. Inject Custom CSS & Themes
      const injectStyles = () => {
        try {
          if (!document.head) return;
          let el = document.getElementById('max-custom-stealth-css');
          if (!el) {
            el = document.createElement('style');
            el.id = 'max-custom-stealth-css';
            document.head.appendChild(el);
          }
          el.textContent = ${cssJson};
        } catch(e) {}
      };

      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectStyles);
      } else {
        injectStyles();
      }

    } catch (e) {
      console.warn('Stealth injection error:', e);
    }
  })();
  `;
}

function applySessionStealth(sessionObj, profileConfig, globalConfig) {
  if (!sessionObj) return;

  const mask = MASKS_DB[profileConfig.mask] || MASKS_DB["Windows 11 (Chrome)"];
  const proxy = profileConfig.proxy && profileConfig.proxy.type !== "Нет" 
    ? profileConfig.proxy 
    : (globalConfig && globalConfig.proxy ? globalConfig.proxy : { type: "Нет" });

  // 1. Configure Proxy
  try {
    if (proxy && proxy.type && proxy.type !== "Нет" && proxy.host && proxy.port) {
      const ptype = proxy.type.toUpperCase();
      let scheme = "http";
      if (ptype === "SOCKS5") scheme = "socks5";
      else if (ptype === "SOCKS4") scheme = "socks4";
      else if (ptype === "HTTPS") scheme = "https";

      const proxyRules = `${scheme}://${proxy.host.trim()}:${proxy.port.trim()}`;
      if (typeof sessionObj.setProxy === "function") {
        sessionObj.setProxy({ proxyRules }).catch(() => {});
      }
    } else {
      if (typeof sessionObj.setProxy === "function") {
        sessionObj.setProxy({ proxyRules: "" }).catch(() => {});
      }
    }
  } catch (e) {
    console.warn("Error setting proxy:", e);
  }

  // 2. Safe WebRTC Policy check
  try {
    if (typeof sessionObj.setWebRTCIPHandlingPolicy === "function") {
      if (profileConfig.webrtc_leak) {
        sessionObj.setWebRTCIPHandlingPolicy("disable_non_proxied_udp");
      } else {
        sessionObj.setWebRTCIPHandlingPolicy("default_public_interface_only");
      }
    }
  } catch (e) {}

  // 3. Spoof UserAgent & Headers at network level
  try {
    if (typeof sessionObj.setUserAgent === "function") {
      sessionObj.setUserAgent(mask.ua, "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7");
    }
  } catch (e) {}

  try {
    if (sessionObj.webRequest && typeof sessionObj.webRequest.onBeforeSendHeaders === "function") {
      sessionObj.webRequest.onBeforeSendHeaders((details, callback) => {
        const headers = { ...details.requestHeaders };
        headers["User-Agent"] = mask.ua;
        headers["Accept-Language"] = "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7";
        headers["Sec-Ch-Ua-Platform"] = mask.platform.includes("Win") ? '"Windows"' : (mask.platform.includes("Mac") ? '"macOS"' : '"Linux"');
        callback({ requestHeaders: headers });
      });
    }
  } catch (e) {
    console.warn("Error attaching onBeforeSendHeaders:", e);
  }
}

module.exports = {
  getStealthInjectionCode,
  applySessionStealth
};
