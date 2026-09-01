using '../main.bicep'

param namePrefix = 'cjtecprd001'
param location = 'westus'
param tags = {
  project: 'data-master'
  domain: 'callcenter'
  env: 'prd'
  managedBy: 'bicep'
}
