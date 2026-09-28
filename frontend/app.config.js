module.exports = ({ config }) => ({
  ...config,

  android: {
    ...config.android,
    package: "com.msafesolutions.legalaid",
    googleServicesFile: "./google-services.json",
  },

  extra: {
    ...config.extra,
    backendUrl: process.env.EXPO_PUBLIC_BACKEND_URL,
    packagerHostname: process.env.EXPO_PACKAGER_HOSTNAME,
  },
});