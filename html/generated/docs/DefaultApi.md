# OpenTricklerRestApi.DefaultApi

All URIs are relative to *http://opentrickler.local/trickler/v1*

Method | HTTP request | Description
------------- | ------------- | -------------
[**getSettings**](DefaultApi.md#getSettings) | **GET** /settings | Read Open Trickler settings
[**updateSettings**](DefaultApi.md#updateSettings) | **PUT** /settings | Update Open Trickler settings



## getSettings

> Setting getSettings()

Read Open Trickler settings

### Example

```javascript
import OpenTricklerRestApi from 'open_trickler_rest_api';

let apiInstance = new OpenTricklerRestApi.DefaultApi();
apiInstance.getSettings((error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Setting**](Setting.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## updateSettings

> updateSettings(setting)

Update Open Trickler settings

### Example

```javascript
import OpenTricklerRestApi from 'open_trickler_rest_api';

let apiInstance = new OpenTricklerRestApi.DefaultApi();
let setting = {"auto_mode":true,"target_weight":10.0,"target_unit":"g"}; // Setting | New setting values
apiInstance.updateSettings(setting, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully.');
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting** | [**Setting**](Setting.md)| New setting values | 

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined

