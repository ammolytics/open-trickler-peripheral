/**
 * Open Trickler REST API
 * A REST API for the Open Trickler that powers a web-based interface and mobile apps (in the future).
 *
 * The version of the OpenAPI document: 1.0.0
 * 
 *
 * NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).
 * https://openapi-generator.tech
 * Do not edit the class manually.
 *
 */

(function(root, factory) {
  if (typeof define === 'function' && define.amd) {
    // AMD.
    define(['expect.js', process.cwd()+'/src/index'], factory);
  } else if (typeof module === 'object' && module.exports) {
    // CommonJS-like environments that support module.exports, like Node.
    factory(require('expect.js'), require(process.cwd()+'/src/index'));
  } else {
    // Browser globals (root is window)
    factory(root.expect, root.OpenTricklerRestApi);
  }
}(this, function(expect, OpenTricklerRestApi) {
  'use strict';

  var instance;

  beforeEach(function() {
    instance = new OpenTricklerRestApi.Setting();
  });

  var getProperty = function(object, getter, property) {
    // Use getter method if present; otherwise, get the property directly.
    if (typeof object[getter] === 'function')
      return object[getter]();
    else
      return object[property];
  }

  var setProperty = function(object, setter, property, value) {
    // Use setter method if present; otherwise, set the property directly.
    if (typeof object[setter] === 'function')
      object[setter](value);
    else
      object[property] = value;
  }

  describe('Setting', function() {
    it('should create an instance of Setting', function() {
      // uncomment below and update the code to test Setting
      //var instance = new OpenTricklerRestApi.Setting();
      //expect(instance).to.be.a(OpenTricklerRestApi.Setting);
    });

    it('should have the property autoMode (base name: "auto_mode")', function() {
      // uncomment below and update the code to test the property autoMode
      //var instance = new OpenTricklerRestApi.Setting();
      //expect(instance).to.be();
    });

    it('should have the property targetWeight (base name: "target_weight")', function() {
      // uncomment below and update the code to test the property targetWeight
      //var instance = new OpenTricklerRestApi.Setting();
      //expect(instance).to.be();
    });

    it('should have the property targetUnit (base name: "target_unit")', function() {
      // uncomment below and update the code to test the property targetUnit
      //var instance = new OpenTricklerRestApi.Setting();
      //expect(instance).to.be();
    });

  });

}));
