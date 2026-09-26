module.exports = ({ config }) => ({
  ...config,
  extra: {
    ...config.extra,
    backendUrl: process.env.EXPO_PUBLIC_BACKEND_URL,
    packagerHostname: process.env.EXPO_PACKAGER_HOSTNAME,
  },
});