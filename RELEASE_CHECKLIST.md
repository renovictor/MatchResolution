# Release Checklist for MatchResolution v1.0.1

## Pre-Release Checks
- [ ] Code review completed
- [ ] All tests passing
- [ ] No breaking changes from previous version
- [ ] Documentation updated
- [ ] VERSION file updated (currently: 1.0.1)
- [ ] README.md reflects current features
- [ ] Dependencies listed in requirements.txt

## Build Process
- [ ] Run `build_exe.ps1` to generate executable
- [ ] Verify executable in `dist\` directory
- [ ] Test executable on clean Windows system
- [ ] Verify application startup and core functionality
- [ ] Check file size is reasonable

## Testing
- [ ] Manual testing of executable
- [ ] Test with sample CSV files
- [ ] Verify all features work as expected in standalone mode
- [ ] Test on target environment (Windows)

## Release
- [ ] Tag release in version control: `v1.0.1`
- [ ] Create release notes
- [ ] Upload executable to release location
- [ ] Update version in VERSION file if needed
- [ ] Notify stakeholders of release

## Post-Release
- [ ] Monitor for issues/bug reports
- [ ] Keep documentation up-to-date
- [ ] Plan next release cycle
- [ ] Archive release artifacts

## Version Rollback (if needed)
- [ ] Identify issue requiring rollback
- [ ] Revert to previous VERSION
- [ ] Notify users of rollback
- [ ] Document incident

## Notes
- Executable created by PyInstaller
- Output location: `dist\MatchResolution.exe`
- Requires Windows OS
