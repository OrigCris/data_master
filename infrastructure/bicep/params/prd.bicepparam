using '../main.bicep'

param namePrefix = 'cjtecprd001'
param location = 'westus'
param alertEmail = 'cristiano.tecnologia.data@hotmail.com'
param tags = {
  project: 'data-master'
  domain: 'callcenter'
  env: 'prd'
  managedBy: 'bicep'
}
