"""
BaSyx AAS LLM Agent - Natural Language Interface
================================================

An intelligent agent that uses OpenAI's GPT to interact with Asset Administration Shells
through natural language commands via Telegram.

INSTALLATION:
    pip install basyx-python-sdk openai python-telegram-bot

SETUP:
    1. Get OpenAI API key from https://platform.openai.com/api-keys
    2. Get Telegram Bot Token from @BotFather on Telegram
    3. Set environment variables:
       export OPENAI_API_KEY="your-openai-api-key"
       export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"

USAGE:
    python basyx_llm_agent.py
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from basyx.aas import model
from basyx.aas.adapter import json as aas_json
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AASAgent:
    """Intelligent agent for managing AAS through natural language"""
    
    def __init__(self):
        self.aas = None
        self.submodels = {}
        self.concept_descriptions = {}  # Store concept descriptions
        self.conversation_history = []
        
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        # Keep only last 20 messages to avoid token limits
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def get_current_state(self) -> str:
        """Get a summary of the current AAS state"""
        if not self.aas:
            return "No AAS exists yet."
        
        state = f"Current AAS: {self.aas.id_short} ({self.aas.id})\n"
        state += f"Asset ID: {self.aas.asset_information.global_asset_id}\n"
        state += f"Number of Submodels: {len(self.submodels)}\n"
        
        if self.submodels:
            state += "\nSubmodels:\n"
            for sm_id, sm in self.submodels.items():
                state += f"  - {sm.id_short}: {len(sm.submodel_element)} elements\n"
                for elem in sm.submodel_element:
                    if isinstance(elem, model.Property):
                        state += f"    • {elem.id_short} ({elem.value_type.__name__}): {elem.value}\n"
        
        return state
    
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Define available functions for OpenAI function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_aas",
                    "description": "Create a new Asset Administration Shell (AAS)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "aas_id": {
                                "type": "string",
                                "description": "Unique identifier for the AAS (URL format)"
                            },
                            "id_short": {
                                "type": "string",
                                "description": "Short human-readable identifier"
                            },
                            "global_asset_id": {
                                "type": "string",
                                "description": "Global identifier for the asset"
                            }
                        },
                        "required": ["aas_id", "id_short", "global_asset_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_submodel",
                    "description": "Add a submodel to the AAS",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "submodel_id": {
                                "type": "string",
                                "description": "Unique identifier for the submodel"
                            },
                            "id_short": {
                                "type": "string",
                                "description": "Short human-readable identifier"
                            }
                        },
                        "required": ["submodel_id", "id_short"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_property",
                    "description": "Add a property element to a submodel",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "submodel_id_short": {
                                "type": "string",
                                "description": "ID short of the submodel to add property to"
                            },
                            "property_name": {
                                "type": "string",
                                "description": "Name/ID short of the property"
                            },
                            "value_type": {
                                "type": "string",
                                "enum": ["string", "int", "float", "boolean"],
                                "description": "Data type of the property"
                            },
                            "value": {
                                "description": "Value to set (can be string, number, or boolean)"
                            },
                            "semantic_id": {
                                "type": "string",
                                "description": "Optional semantic ID reference to concept description"
                            }
                        },
                        "required": ["submodel_id_short", "property_name", "value_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_property",
                    "description": "Update the value of an existing property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "submodel_id_short": {
                                "type": "string",
                                "description": "ID short of the submodel containing the property"
                            },
                            "property_name": {
                                "type": "string",
                                "description": "Name/ID short of the property to update"
                            },
                            "value": {
                                "description": "New value to set"
                            }
                        },
                        "required": ["submodel_id_short", "property_name", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_property_value",
                    "description": "Get the current value of a property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "submodel_id_short": {
                                "type": "string",
                                "description": "ID short of the submodel"
                            },
                            "property_name": {
                                "type": "string",
                                "description": "Name/ID short of the property"
                            }
                        },
                        "required": ["submodel_id_short", "property_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_aas",
                    "description": "Save the AAS to a JSON file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name of the file to save (should end with .json)"
                            }
                        },
                        "required": ["filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "load_aas",
                    "description": "Load an AAS from a JSON file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name of the file to load"
                            }
                        },
                        "required": ["filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tree_view",
                    "description": "Get a tree view representation of the entire AAS structure",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_state",
                    "description": "Get a summary of the current AAS state including all submodels and properties",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_concept_description",
                    "description": "Add a concept description to define semantic meaning of properties",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "concept_id": {
                                "type": "string",
                                "description": "Unique identifier for the concept"
                            },
                            "id_short": {
                                "type": "string",
                                "description": "Short identifier"
                            },
                            "preferred_name": {
                                "type": "string",
                                "description": "Human-readable name"
                            },
                            "definition": {
                                "type": "string",
                                "description": "Definition of the concept"
                            }
                        },
                        "required": ["concept_id", "id_short"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_semantic_id",
                    "description": "Update or add semantic ID reference to an existing property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "submodel_id_short": {
                                "type": "string",
                                "description": "ID short of the submodel"
                            },
                            "property_name": {
                                "type": "string",
                                "description": "Name of the property to update"
                            },
                            "semantic_id": {
                                "type": "string",
                                "description": "Semantic ID reference (usually concept description ID)"
                            }
                        },
                        "required": ["submodel_id_short", "property_name", "semantic_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_digital_twin_json",
                    "description": "Get the complete Digital Twin (AAS) as JSON format string",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    
    # Function implementations
    
    def create_aas(self, aas_id: str, id_short: str, global_asset_id: str) -> str:
        """Create a new AAS"""
        try:
            asset_information = model.AssetInformation(
                asset_kind=model.AssetKind.INSTANCE,
                global_asset_id=global_asset_id
            )
            
            self.aas = model.AssetAdministrationShell(
                id_=aas_id,
                id_short=id_short,
                asset_information=asset_information
            )
            
            return f"✅ Created AAS '{id_short}' with ID: {aas_id}"
        except Exception as e:
            return f"❌ Error creating AAS: {str(e)}"
    
    def add_submodel(self, submodel_id: str, id_short: str) -> str:
        """Add a submodel to the AAS"""
        try:
            if not self.aas:
                return "❌ No AAS exists. Please create an AAS first."
            
            submodel = model.Submodel(
                id_=submodel_id,
                id_short=id_short
            )
            
            self.submodels[submodel_id] = submodel
            self.aas.submodel.add(model.ModelReference.from_referable(submodel))
            
            return f"✅ Added submodel '{id_short}' to AAS"
        except Exception as e:
            return f"❌ Error adding submodel: {str(e)}"
    
    def add_property(self, submodel_id_short: str, property_name: str, 
                     value_type: str, value=None, semantic_id: str = None) -> str:
        """Add a property to a submodel"""
        try:
            # Find submodel by id_short
            submodel = None
            for sm in self.submodels.values():
                if sm.id_short == submodel_id_short:
                    submodel = sm
                    break
            
            if not submodel:
                return f"❌ Submodel '{submodel_id_short}' not found"
            
            # Map string type to model type
            type_map = {
                "string": model.datatypes.String,
                "int": model.datatypes.Int,
                "float": model.datatypes.Float,
                "boolean": model.datatypes.Boolean
            }
            
            value_type_obj = type_map.get(value_type.lower())
            if not value_type_obj:
                return f"❌ Invalid value type: {value_type}"
            
            # Convert value to appropriate type
            converted_value = None
            if value is not None:
                if value_type.lower() == "int":
                    converted_value = int(value)
                elif value_type.lower() == "float":
                    converted_value = float(value)
                elif value_type.lower() == "boolean":
                    converted_value = bool(value) if isinstance(value, bool) else str(value).lower() in ('true', 't', 'yes', '1')
                else:
                    converted_value = str(value)
            
            property_element = model.Property(
                id_short=property_name,
                value_type=value_type_obj,
                value=converted_value
            )
            
            # Add semantic ID if provided
            if semantic_id:
                property_element.semantic_id = model.ExternalReference((
                    model.Key(
                        type_=model.KeyTypes.GLOBAL_REFERENCE,
                        value=semantic_id
                    ),
                ))
            
            submodel.submodel_element.add(property_element)
            
            value_str = f" with value {converted_value}" if converted_value is not None else ""
            semantic_str = f"\n   Semantic ID: {semantic_id}" if semantic_id else ""
            return f"✅ Added property '{property_name}' ({value_type}) to submodel '{submodel_id_short}'{value_str}{semantic_str}"
        except Exception as e:
            return f"❌ Error adding property: {str(e)}"
    
    def update_property(self, submodel_id_short: str, property_name: str, value) -> str:
        """Update a property value"""
        try:
            # Find submodel
            submodel = None
            for sm in self.submodels.values():
                if sm.id_short == submodel_id_short:
                    submodel = sm
                    break
            
            if not submodel:
                return f"❌ Submodel '{submodel_id_short}' not found"
            
            # Find property
            property_elem = submodel.submodel_element.get_object_by_attribute('id_short', property_name)
            
            if not property_elem:
                return f"❌ Property '{property_name}' not found in submodel '{submodel_id_short}'"
            
            if not isinstance(property_elem, model.Property):
                return f"❌ Element '{property_name}' is not a Property"
            
            old_value = property_elem.value
            
            # Convert value based on property type
            if property_elem.value_type == model.datatypes.Int:
                property_elem.value = int(value)
            elif property_elem.value_type == model.datatypes.Float:
                property_elem.value = float(value)
            elif property_elem.value_type == model.datatypes.Boolean:
                property_elem.value = bool(value) if isinstance(value, bool) else str(value).lower() in ('true', 't', 'yes', '1')
            else:
                property_elem.value = str(value)
            
            return f"✅ Updated '{property_name}': {old_value} → {property_elem.value}"
        except Exception as e:
            return f"❌ Error updating property: {str(e)}"
    
    def get_property_value(self, submodel_id_short: str, property_name: str) -> str:
        """Get a property value"""
        try:
            # Find submodel
            submodel = None
            for sm in self.submodels.values():
                if sm.id_short == submodel_id_short:
                    submodel = sm
                    break
            
            if not submodel:
                return f"❌ Submodel '{submodel_id_short}' not found"
            
            # Find property
            property_elem = submodel.submodel_element.get_object_by_attribute('id_short', property_name)
            
            if not property_elem:
                return f"❌ Property '{property_name}' not found"
            
            if isinstance(property_elem, model.Property):
                return f"📌 {property_name} = {property_elem.value} ({property_elem.value_type.__name__})"
            else:
                return f"Element '{property_name}' is not a Property"
        except Exception as e:
            return f"❌ Error getting property: {str(e)}"
    
    def save_aas(self, filename: str) -> str:
        """Save AAS to file"""
        try:
            if not self.aas:
                return "❌ No AAS to save"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            object_store = model.DictObjectStore()
            object_store.add(self.aas)
            
            for submodel in self.submodels.values():
                object_store.add(submodel)
            
            for concept in self.concept_descriptions.values():
                object_store.add(concept)
            
            with open(filename, 'w', encoding='utf-8') as json_file:
                aas_json.write_aas_json_file(json_file, object_store)
            
            cd_count = len(self.concept_descriptions)
            cd_info = f", {cd_count} concept(s)" if cd_count > 0 else ""
            return f"✅ Saved AAS to '{filename}' ({len(self.submodels)} submodels{cd_info})"
        except Exception as e:
            return f"❌ Error saving: {str(e)}"
    
    def load_aas(self, filename: str) -> str:
        """Load AAS from file"""
        try:
            with open(filename, 'r', encoding='utf-8-sig') as json_file:
                loaded_store = aas_json.read_aas_json_file(json_file)
            
            # Extract AAS
            self.aas = None
            for obj in loaded_store:
                if isinstance(obj, model.AssetAdministrationShell):
                    self.aas = obj
                    break
            
            # Extract Submodels
            self.submodels = {}
            for obj in loaded_store:
                if isinstance(obj, model.Submodel):
                    self.submodels[obj.id] = obj
            
            # Extract Concept Descriptions
            self.concept_descriptions = {}
            for obj in loaded_store:
                if isinstance(obj, model.ConceptDescription):
                    self.concept_descriptions[obj.id] = obj
            
            if self.aas:
                total_elements = sum(len(sm.submodel_element) for sm in self.submodels.values())
                cd_count = len(self.concept_descriptions)
                cd_info = f", {cd_count} concept(s)" if cd_count > 0 else ""
                return f"✅ Loaded '{self.aas.id_short}' from '{filename}' ({len(self.submodels)} submodels, {total_elements} elements{cd_info})"
            else:
                return "❌ No AAS found in file"
        except FileNotFoundError:
            return f"❌ File '{filename}' not found"
        except Exception as e:
            return f"❌ Error loading: {str(e)}"
    
    def get_tree_view(self) -> str:
        """Generate tree view of AAS"""
        if not self.aas:
            return "❌ No AAS available"
        
        lines = []
        lines.append("📦 Asset Administration Shell")
        lines.append("│")
        lines.append(f"├─ ID Short: {self.aas.id_short}")
        lines.append(f"├─ ID: {self.aas.id}")
        
        if self.aas.asset_information:
            lines.append("├─ 🏭 Asset Information")
            lines.append(f"│  ├─ Global Asset ID: {self.aas.asset_information.global_asset_id}")
            lines.append(f"│  └─ Asset Kind: {self.aas.asset_information.asset_kind.name}")
        
        if self.submodels:
            lines.append("│")
            submodel_list = list(self.submodels.values())
            for sm_idx, submodel in enumerate(submodel_list, 1):
                is_last_submodel = (sm_idx == len(submodel_list))
                sm_prefix = "└─" if is_last_submodel else "├─"
                continuation = "   " if is_last_submodel else "│  "
                
                lines.append(f"{sm_prefix} 📋 Submodel: {submodel.id_short}")
                lines.append(f"{continuation}├─ ID: {submodel.id}")
                
                elements = list(submodel.submodel_element)
                if elements:
                    lines.append(f"{continuation}├─ Elements: {len(elements)}")
                    lines.append(f"{continuation}│")
                    
                    for elem_idx, element in enumerate(elements, 1):
                        is_last_element = (elem_idx == len(elements))
                        elem_prefix = "└─" if is_last_element else "├─"
                        
                        if isinstance(element, model.Property):
                            value_display = element.value if element.value is not None else "None"
                            type_name = element.value_type.__name__ if element.value_type else "Unknown"
                            
                            lines.append(f"{continuation}│  {elem_prefix} 📌 {element.id_short}")
                            
                            if not is_last_element:
                                lines.append(f"{continuation}│  │  ├─ Type: {type_name}")
                                lines.append(f"{continuation}│  │  └─ Value: {value_display}")
                            else:
                                lines.append(f"{continuation}│     ├─ Type: {type_name}")
                                lines.append(f"{continuation}│     └─ Value: {value_display}")
                else:
                    lines.append(f"{continuation}└─ Elements: 0 (empty)")
                
                if not is_last_submodel:
                    lines.append("│")
        else:
            lines.append("└─ Submodels: 0 (empty)")
        
        total_elements = sum(len(sm.submodel_element) for sm in self.submodels.values())
        lines.append("")
        lines.append(f"Summary: {len(self.submodels)} Submodel(s), {total_elements} Element(s)")
        
        return "\n".join(lines)
    
    def add_concept_description(self, concept_id: str, id_short: str, 
                                preferred_name: str = None, definition: str = None) -> str:
        """Add a concept description to the AAS"""
        try:
            # Create concept description
            concept = model.ConceptDescription(
                id_=concept_id,
                id_short=id_short
            )
            
            # Add preferred name if provided
            if preferred_name:
                concept.display_name = model.MultiLanguageNameType({
                    "en": preferred_name
                })
            
            # Add definition if provided
            if definition:
                concept.description = model.MultiLanguageTextType({
                    "en": definition
                })
            
            # Store concept description
            self.concept_descriptions[concept_id] = concept
            
            result = f"✅ Added concept description '{id_short}'"
            if preferred_name:
                result += f"\n   Name: {preferred_name}"
            if definition:
                result += f"\n   Definition: {definition}"
            
            return result
        except Exception as e:
            return f"❌ Error adding concept description: {str(e)}"
    
    def update_semantic_id(self, submodel_id_short: str, property_name: str, semantic_id: str) -> str:
        """Update or add semantic ID to an existing property"""
        try:
            # Find submodel
            submodel = None
            for sm in self.submodels.values():
                if sm.id_short == submodel_id_short:
                    submodel = sm
                    break
            
            if not submodel:
                return f"❌ Submodel '{submodel_id_short}' not found"
            
            # Find property
            property_elem = submodel.submodel_element.get_object_by_attribute('id_short', property_name)
            
            if not property_elem:
                return f"❌ Property '{property_name}' not found in submodel '{submodel_id_short}'"
            
            if not isinstance(property_elem, model.Property):
                return f"❌ Element '{property_name}' is not a Property"
            
            # Update semantic ID
            property_elem.semantic_id = model.ExternalReference((
                model.Key(
                    type_=model.KeyTypes.GLOBAL_REFERENCE,
                    value=semantic_id
                ),
            ))
            
            return f"✅ Updated semantic ID for '{property_name}'\n   Semantic ID: {semantic_id}"
        except Exception as e:
            return f"❌ Error updating semantic ID: {str(e)}"
    
    def get_digital_twin_json(self) -> str:
        """Get the complete Digital Twin as formatted JSON"""
        try:
            if not self.aas:
                return "❌ No AAS available to export"
            
            # Create object store with all components
            object_store = model.DictObjectStore()
            object_store.add(self.aas)
            
            # Add all submodels
            for submodel in self.submodels.values():
                object_store.add(submodel)
            
            # Add all concept descriptions
            for concept in self.concept_descriptions.values():
                object_store.add(concept)
            
            # Convert to JSON string
            import io
            json_buffer = io.StringIO()
            aas_json.write_aas_json_file(json_buffer, object_store)
            json_string = json_buffer.getvalue()
            
            # Pretty print the JSON
            import json as json_module
            json_obj = json_module.loads(json_string)
            pretty_json = json_module.dumps(json_obj, indent=2)
            
            result = "📄 **Digital Twin JSON:**\n\n```json\n" + pretty_json + "\n```\n\n"
            result += f"✅ Complete Digital Twin with:\n"
            result += f"   • 1 AAS: {self.aas.id_short}\n"
            result += f"   • {len(self.submodels)} Submodel(s)\n"
            
            total_elements = sum(len(sm.submodel_element) for sm in self.submodels.values())
            result += f"   • {total_elements} Element(s)\n"
            result += f"   • {len(self.concept_descriptions)} Concept Description(s)\n"
            
            return result
        except Exception as e:
            return f"❌ Error generating JSON: {str(e)}"
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a function based on LLM's decision"""
        function_map = {
            "create_aas": self.create_aas,
            "add_submodel": self.add_submodel,
            "add_property": self.add_property,
            "update_property": self.update_property,
            "get_property_value": self.get_property_value,
            "save_aas": self.save_aas,
            "load_aas": self.load_aas,
            "get_tree_view": self.get_tree_view,
            "get_current_state": self.get_current_state,
            "add_concept_description": self.add_concept_description,
            "update_semantic_id": self.update_semantic_id,
            "get_digital_twin_json": self.get_digital_twin_json
        }
        
        func = function_map.get(function_name)
        if not func:
            return f"❌ Unknown function: {function_name}"
        
        try:
            return func(**arguments)
        except Exception as e:
            return f"❌ Error executing {function_name}: {str(e)}"
    
    async def process_message(self, user_message: str) -> str:
        """Process user message using OpenAI with function calling"""
        try:
            # Add user message to history
            self.add_to_history("user", user_message)
            
            # Prepare system message with current state
            system_message = f"""You are an intelligent assistant for managing Asset Administration Shells (AAS) using the BaSyx standard.

Current AAS State:
{self.get_current_state()}

You can help users with these operations:
1. Create AAS
2. Add submodels
3. Add properties/elements to submodels
4. Update property values
5. Get property values
6. Save AAS to file
7. Load AAS from file
8. Show tree view of AAS structure
9. Get current state summary

When users ask to do something, call the appropriate function. Be conversational and friendly.
If the user's request requires generating IDs (like AAS ID or Submodel ID), create them in a proper URL format like:
- https://example.com/aas/[descriptive-name]
- https://example.com/submodels/[descriptive-name]

Always confirm what you've done and provide helpful feedback."""

            messages = [
                {"role": "system", "content": system_message}
            ] + self.conversation_history
            
            # Call OpenAI with function calling
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.get_available_functions(),
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Check if the model wants to call functions
            if assistant_message.tool_calls:
                # Execute all function calls
                function_results = []
                
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    result = self.execute_function(function_name, function_args)
                    function_results.append((tool_call.id, result))
                
                # Add assistant message with tool calls (proper format)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                # Add tool responses
                for tool_call_id, result in function_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result
                    })
                
                # Get final response from model
                second_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                
                final_answer = second_response.choices[0].message.content
                self.add_to_history("assistant", final_answer)
                
                return final_answer
            else:
                # No function call, return the response directly
                response_text = assistant_message.content
                self.add_to_history("assistant", response_text)
                return response_text
                
        except Exception as e:
            return f"❌ Error processing message: {str(e)}"


# Global agent instance
agent = AASAgent()


# Telegram Bot Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    # Get user information
    user = update.effective_user
    print(f"User {user.id} ({user.full_name}) started the bot")
    welcome_message = """
🤖 Welcome to BaSyx AAS Agent!

I'm an AI assistant that helps you manage Asset Administration Shells using natural language.

You can ask me to:
• Create an AAS for a motor
• Add a submodel for technical data
• Add properties like temperature, serial number
• Update values
• Save and load AAS files
• Show the structure as a tree

Just tell me what you want to do in plain English!

Examples:
- "Create an AAS for an electric motor"
- "Add a temperature property with value 25.5"
- "Show me the current structure"
- "Save this as motor.json"

Try: /help for more information
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 BaSyx AAS Agent - Help

**What I can do:**

🔧 Create & Manage
- Create new AAS
- Add submodels
- Add properties (String, Integer, Float, Boolean)

📝 Data Operations
- Set property values
- Update existing values
- Get current values

💾 File Operations
- Save AAS to JSON file
- Load AAS from JSON file

📊 View & Query
- Show tree view of structure
- Get current state summary
- Query specific properties

**Example Commands:**

"Create an AAS for a temperature sensor with ID sensor-001"
"Add a submodel called SensorData"
"Add a float property Temperature with value 23.5"
"Update the Temperature to 25.0"
"Show me the tree view"
"Save this as sensor.json"
"Load motor.json"

**Tips:**
- Be natural! Just describe what you want
- I'll figure out the technical details
- You can refer to things by name (like "update temperature")

Type /state to see the current AAS state
Type /tree to see the tree view
Type /reset to start over
"""
    await update.message.reply_text(help_text)


async def state_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /state command"""
    state = agent.get_current_state()
    await update.message.reply_text(f"**Current State:**\n\n{state}", parse_mode="Markdown")


async def tree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tree command"""
    tree = agent.get_tree_view()
    await update.message.reply_text(f"```\n{tree}\n```", parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command"""
    global agent
    agent = AASAgent()
    await update.message.reply_text("✅ Reset complete! Starting fresh with no AAS.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    user_message = update.message.text
    print(f"✅ Received message from {update.effective_user.id},  {update.effective_user.username}: {user_message}")
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    # Process with LLM agent
    response = await agent.process_message(user_message)
    
    # Send response
    await update.message.reply_text(response)


def main():
    """Main function to run the Telegram bot"""
    # Check for required environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not openai_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    if not telegram_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        print("Set it with: export TELEGRAM_BOT_TOKEN='your-token-here'")
        return
    
    print("🤖 Starting BaSyx AAS LLM Agent...")
    print(f"✅ OpenAI API Key: {openai_key[:8]}...{openai_key[-4:]}")
    print(f"✅ Telegram Bot Token: {telegram_token[:8]}...{telegram_token[-4:]}")
    
    # Create application
    application = Application.builder().token(telegram_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("state", state_command))
    application.add_handler(CommandHandler("tree", tree_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("✅ Bot is running! Send messages to your Telegram bot.")
    print("Press Ctrl+C to stop.")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
