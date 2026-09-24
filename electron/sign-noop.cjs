/**
 * No-op sign hook for electron-builder on Windows.
 * Bypasses winCodeSign download and extraction when no certificate is used.
 */
module.exports = async function(configuration) {
  // Skipping code signing during local build
  return;
};
