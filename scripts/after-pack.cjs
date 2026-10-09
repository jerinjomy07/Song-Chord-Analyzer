const { execSync } = require('child_process');
const path = require('path');

exports.default = async function(context) {
  if (context.electronPlatformName === 'darwin') {
    const appPath = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`);
    console.log(`[afterPack] Applying native ad-hoc code signature to ${appPath}...`);
    try {
      execSync(`codesign --force --deep --sign - "${appPath}"`, { stdio: 'inherit' });
      console.log(`[afterPack] Ad-hoc code signature successfully applied to ${appPath}`);
    } catch (err) {
      console.warn(`[afterPack] Warning: Failed to apply ad-hoc signature:`, err.message);
    }
  }
};
