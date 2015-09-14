Core Structure
==============
Validator - Allow Spec objects a list of validators to be called once an object is built
Specs  - Renders the loaded (re: Loader) spec into workable objects. Further checking if nessecary (eg, SwaggerSpec)

Tooling
=======
Linter - Define and check for API styles. Need to allow for disabling and general configuration
CodeGen
	- Server
		-- Ship with Unit Tests
	- Client
		-- Ship with Unit Tests
	- System Tests
Documentation - Render the loaded spec into a navigateable UI with end user documentation

Ramblings
=========
Logging Decorator - Log an instance's method/arguments when called
Logging Metaclass - Give each instance the correct logger when created. Use logging decorator
