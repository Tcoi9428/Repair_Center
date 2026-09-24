import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'../..');
const skill='C:/Users/i.petrikin/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
 explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 workspaceDir:root,candidatePath:path.join(root,'presentations/build/candidate.pptx'),
 finalPath:path.join(root,'output/presentations/Remontny-Centr-concept-7-slides-v3.pptx'),
 pythonExecutable:'C:/Users/i.petrikin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:['Segoe UI']},verifyArtifactToolImport:true,
 receiptPath:path.join(root,'presentations/build/v3.validation.json')
});
console.log(JSON.stringify(result));
