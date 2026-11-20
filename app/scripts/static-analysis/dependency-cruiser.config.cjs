/**
 * Read-only module-boundary baseline for the JavaScript/TypeScript packages.
 * Keep this policy intentionally small: it identifies cycles and accidental
 * imports between independently built app packages. It is not a release gate
 * until the first report has been triaged.
 */
const packages = ["frontend", "docs-site", "release-signing-worker"];

const crossPackageRules = packages.flatMap((fromPackage) =>
  packages
    .filter((toPackage) => toPackage !== fromPackage)
    .map((toPackage) => ({
      name: `no-${fromPackage}-to-${toPackage}`,
      comment: "Independently deployed packages must communicate through an API contract.",
      severity: "warn",
      from: { path: `^app/${fromPackage}/` },
      to: { path: `^app/${toPackage}/` }
    }))
);

module.exports = {
  forbidden: [
    {
      name: "no-circular",
      comment: "Cycles make package ownership and release boundaries ambiguous.",
      severity: "error",
      from: { pathNot: "(^|/)node_modules/" },
      to: { circular: true }
    },
    ...crossPackageRules
  ],
  options: {
    tsPreCompilationDeps: true,
    doNotFollow: [
      "(^|/)node_modules/",
      "(^|/)(dist|dist-site|build|generated|runtime|DebateAI_Generated|\\.astro)/"
    ],
    enhancedResolveOptions: {
      extensions: [".js", ".mjs", ".cjs", ".ts", ".tsx", ".astro"]
    }
  }
};
