"""
Input Validator Service - Command validation and suggestions for Claude Code
Implementa CHAT-03 input features: validation, autocompletado, y command recognition
Siguiendo standards/fastapi.yaml y standards/python.yaml
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from models.chat import (
    CommandSuggestion, InputValidationResult, InputHistoryEntry
)


@dataclass
class CommandDefinition:
    """Definición de comando de Claude Code para validación"""
    name: str
    category: str
    description: str
    usage_hint: str
    parameters: List[str]
    examples: List[str]
    pattern: str
    confidence_base: float = 1.0


class InputValidator:
    """
    Servicio de validación de input para comandos de Claude Code
    Async patterns para validation y suggestion generation
    """

    def __init__(self) -> None:
        # Base de datos de comandos Claude Code (basada en el toolkit)
        self._command_definitions = self._load_command_definitions()
        self._command_patterns = self._compile_patterns()

    def _load_command_definitions(self) -> Dict[str, CommandDefinition]:
        """
        Cargar definiciones de comandos del Claude Code Toolkit
        Basado en los 16 comandos y 10 agentes del sistema
        """
        commands = {}

        # A-commands: Planning, management, and orchestration
        a_commands = [
            CommandDefinition(
                name="/A-plan",
                category="A-commands",
                description="Strategic project planning and development roadmaps",
                usage_hint="/A-plan \"project description\"",
                parameters=["project_description"],
                examples=["/A-plan \"Build a REST API for user management\""],
                pattern=r"^/A-plan\s+.+",
                confidence_base=0.95
            ),
            CommandDefinition(
                name="/A-ai-code",
                category="A-commands",
                description="Master orchestrator with agent delegation matrix",
                usage_hint="/A-ai-code \"coding task\"",
                parameters=["coding_task"],
                examples=["/A-ai-code \"Create a FastAPI endpoint for user login\""],
                pattern=r"^/A-ai-code\s+.+",
                confidence_base=0.95
            ),
            CommandDefinition(
                name="/A-claude-auto",
                category="A-commands",
                description="Universal router with 90%+ intent recognition",
                usage_hint="/A-claude-auto \"request\"",
                parameters=["request"],
                examples=["/A-claude-auto \"I need help with authentication\""],
                pattern=r"^/A-claude-auto\s+.+",
                confidence_base=0.9
            ),
            CommandDefinition(
                name="/A-workflow",
                category="A-commands",
                description="Specialized agent coordination for complex workflows",
                usage_hint="/A-workflow \"workflow description\"",
                parameters=["workflow_description"],
                examples=["/A-workflow \"Set up CI/CD pipeline\""],
                pattern=r"^/A-workflow\s+.+",
                confidence_base=0.9
            ),
            CommandDefinition(
                name="/A-insights",
                category="A-commands",
                description="Real developer analytics from git patterns and codebase hotspots",
                usage_hint="/A-insights [scope]",
                parameters=["scope"],
                examples=["/A-insights", "/A-insights security"],
                pattern=r"^/A-insights(\s+\w+)?$",
                confidence_base=0.85
            ),
            CommandDefinition(
                name="/A-onboarding",
                category="A-commands",
                description="Project analysis without assuming existing documentation",
                usage_hint="/A-onboarding [project_path]",
                parameters=["project_path"],
                examples=["/A-onboarding", "/A-onboarding /path/to/project"],
                pattern=r"^/A-onboarding(\s+.+)?$",
                confidence_base=0.85
            ),
            CommandDefinition(
                name="/A-todo",
                category="A-commands",
                description="Advanced productivity augmenter with Eisenhower Matrix",
                usage_hint="/A-todo [action] [task]",
                parameters=["action", "task"],
                examples=["/A-todo add \"Fix login bug\"", "/A-todo list"],
                pattern=r"^/A-todo(\s+\w+(\s+.+)?)?$",
                confidence_base=0.8
            )
        ]

        # B-commands: Tools and analysis
        b_commands = [
            CommandDefinition(
                name="/B-create-feature",
                category="B-commands",
                description="Auto-detection of architecture with template generation",
                usage_hint="/B-create-feature \"feature description\"",
                parameters=["feature_description"],
                examples=["/B-create-feature \"User authentication system\""],
                pattern=r"^/B-create-feature\s+.+",
                confidence_base=0.9
            ),
            CommandDefinition(
                name="/B-explain-code",
                category="B-commands",
                description="Comprehensive code analysis and explanation",
                usage_hint="/B-explain-code [file_path]",
                parameters=["file_path"],
                examples=["/B-explain-code app.py", "/B-explain-code"],
                pattern=r"^/B-explain-code(\s+.+)?$",
                confidence_base=0.85
            ),
            CommandDefinition(
                name="/B-debug-error",
                category="B-commands",
                description="Advanced error analysis and debugging assistance",
                usage_hint="/B-debug-error \"error description\"",
                parameters=["error_description"],
                examples=["/B-debug-error \"AttributeError in user model\""],
                pattern=r"^/B-debug-error\s+.+",
                confidence_base=0.9
            ),
            CommandDefinition(
                name="/B-ultra-think",
                category="B-commands",
                description="Deep analysis framework with multi-perspective methodology",
                usage_hint="/B-ultra-think \"complex problem\"",
                parameters=["problem_description"],
                examples=["/B-ultra-think \"Optimize database queries for performance\""],
                pattern=r"^/B-ultra-think\s+.+",
                confidence_base=0.85
            ),
            CommandDefinition(
                name="/B-refactor",
                category="B-commands",
                description="Code refactoring with best practices analysis",
                usage_hint="/B-refactor [file_path]",
                parameters=["file_path"],
                examples=["/B-refactor models.py", "/B-refactor"],
                pattern=r"^/B-refactor(\s+.+)?$",
                confidence_base=0.8
            ),
            CommandDefinition(
                name="/B-test-gen",
                category="B-commands",
                description="Automated test generation for code coverage",
                usage_hint="/B-test-gen [target]",
                parameters=["target"],
                examples=["/B-test-gen api.py", "/B-test-gen"],
                pattern=r"^/B-test-gen(\s+.+)?$",
                confidence_base=0.8
            )
        ]

        # M1-agents: Specialized delegation targets
        m1_agents = [
            CommandDefinition(
                name="M1-qa-gatekeeper",
                category="M1-agents",
                description="Zero-tolerance quality validation with FIRST PRIORITY standards",
                usage_hint="M1-qa-gatekeeper \"quality check request\"",
                parameters=["quality_request"],
                examples=["M1-qa-gatekeeper \"Review code quality\""],
                pattern=r"^M1-qa-gatekeeper\s+.+",
                confidence_base=0.95
            ),
            CommandDefinition(
                name="M1-ultrathink-orchestrator",
                category="M1-agents",
                description="Supreme multi-tool coordination with CRITICAL FIRST STEP",
                usage_hint="M1-ultrathink-orchestrator \"complex coordination task\"",
                parameters=["coordination_task"],
                examples=["M1-ultrathink-orchestrator \"Coordinate microservices deployment\""],
                pattern=r"^M1-ultrathink-orchestrator\s+.+",
                confidence_base=0.95
            ),
            CommandDefinition(
                name="M1-general-purpose-agent",
                category="M1-agents",
                description="Capability Matrix approach with anti-vagueness framework",
                usage_hint="M1-general-purpose-agent \"general task\"",
                parameters=["task"],
                examples=["M1-general-purpose-agent \"Help with project setup\""],
                pattern=r"^M1-general-purpose-agent\s+.+",
                confidence_base=0.8
            ),
            CommandDefinition(
                name="M1-ux-strategy-protocol",
                category="M1-agents",
                description="Think Harder UX framework with gap analysis",
                usage_hint="M1-ux-strategy-protocol \"UX task\"",
                parameters=["ux_task"],
                examples=["M1-ux-strategy-protocol \"Design user onboarding flow\""],
                pattern=r"^M1-ux-strategy-protocol\s+.+",
                confidence_base=0.85
            ),
            CommandDefinition(
                name="M1-human-behavior-simulator",
                category="M1-agents",
                description="Hybrid real-synthetic data approach with transparency",
                usage_hint="M1-human-behavior-simulator \"behavior analysis\"",
                parameters=["behavior_analysis"],
                examples=["M1-human-behavior-simulator \"Analyze user interaction patterns\""],
                pattern=r"^M1-human-behavior-simulator\s+.+",
                confidence_base=0.8
            )
        ]

        # Combinar todos los comandos
        all_commands = a_commands + b_commands + m1_agents

        # Crear diccionario con nombre como clave
        for cmd in all_commands:
            commands[cmd.name] = cmd

        return commands

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compilar patrones regex para performance optimizada"""
        patterns = {}
        for cmd_name, cmd_def in self._command_definitions.items():
            patterns[cmd_name] = re.compile(cmd_def.pattern, re.IGNORECASE)
        return patterns

    async def validate_input(self, input_text: str, partial: bool = False) -> InputValidationResult:
        """
        Validar input para comandos de Claude Code
        Async pattern para validation en tiempo real
        """
        input_text = input_text.strip()

        # Detectar tipo de validación
        validation_type = self._determine_validation_type(input_text)

        # Realizar validación específica
        if validation_type == "command":
            return await self._validate_command(input_text, partial)
        elif validation_type == "partial_command":
            return await self._validate_partial_command(input_text)
        else:
            return await self._validate_general_input(input_text)

    def _determine_validation_type(self, input_text: str) -> str:
        """Determinar el tipo de validación requerida"""
        if input_text.startswith(('/A-', '/B-', 'M1-')):
            if ' ' in input_text or input_text.endswith(' '):
                return "command"
            else:
                return "partial_command"
        elif input_text.startswith('/'):
            return "partial_command"
        else:
            return "general"

    async def _validate_command(self, input_text: str, partial: bool) -> InputValidationResult:
        """Validar comando completo de Claude Code"""
        errors = []
        warnings = []
        suggestions = []

        # Buscar coincidencia exacta
        matched_command = None
        for cmd_name, cmd_def in self._command_definitions.items():
            if self._command_patterns[cmd_name].match(input_text):
                matched_command = cmd_def
                break

        if matched_command:
            # Comando válido encontrado
            return InputValidationResult(
                is_valid=True,
                validation_type="command_match",
                suggestions=[self._create_command_suggestion(matched_command)]
            )
        else:
            # Buscar comandos similares
            similar_commands = await self._find_similar_commands(input_text)
            suggestions.extend(similar_commands)

            # Analizar errores comunes
            errors = self._analyze_command_errors(input_text)

            return InputValidationResult(
                is_valid=False,
                validation_type="command_error",
                errors=errors,
                suggestions=suggestions,
                corrected_input=suggestions[0].command if suggestions else None
            )

    async def _validate_partial_command(self, input_text: str) -> InputValidationResult:
        """Validar comando parcial para autocompletado"""
        suggestions = await self._get_command_suggestions(input_text, limit=5)

        return InputValidationResult(
            is_valid=len(suggestions) > 0,
            validation_type="partial_match",
            suggestions=suggestions
        )

    async def _validate_general_input(self, input_text: str) -> InputValidationResult:
        """Validar input general (no comando)"""
        return InputValidationResult(
            is_valid=True,
            validation_type="general_text",
            suggestions=[]
        )

    async def _find_similar_commands(self, input_text: str, max_results: int = 3) -> List[CommandSuggestion]:
        """Encontrar comandos similares usando similarity scoring"""
        similarities = []

        for cmd_name, cmd_def in self._command_definitions.items():
            similarity = self._calculate_similarity(input_text, cmd_name)
            if similarity > 0.3:  # Threshold para relevancia
                similarities.append((similarity, cmd_def))

        # Ordenar por similarity y tomar los mejores
        similarities.sort(key=lambda x: x[0], reverse=True)

        suggestions = []
        for similarity, cmd_def in similarities[:max_results]:
            suggestion = self._create_command_suggestion(cmd_def)
            suggestion.confidence = similarity
            suggestions.append(suggestion)

        return suggestions

    def _calculate_similarity(self, input_text: str, command_name: str) -> float:
        """Calcular similarity básica entre input y comando"""
        input_lower = input_text.lower()
        cmd_lower = command_name.lower()

        # Similarity basada en prefijo común
        if cmd_lower.startswith(input_lower):
            return 0.9

        # Similarity basada en substring
        if input_lower in cmd_lower:
            return 0.7

        # Similarity basada en distancia de Levenshtein simplificada
        common_chars = set(input_lower) & set(cmd_lower)
        if common_chars:
            return len(common_chars) / max(len(input_lower), len(cmd_lower))

        return 0.0

    def _analyze_command_errors(self, input_text: str) -> List[str]:
        """Analizar errores comunes en comandos"""
        errors = []

        # Error: Comando no encontrado
        if input_text.startswith(('/A-', '/B-', 'M1-')):
            errors.append(f"Comando '{input_text.split()[0]}' no reconocido")

        # Error: Falta parámetro
        if len(input_text.split()) == 1 and input_text.startswith(('/A-', '/B-')):
            errors.append("Este comando requiere parámetros adicionales")

        # Error: Sintaxis incorrecta
        if ' ' not in input_text and input_text.count('-') < 2:
            errors.append("Sintaxis de comando incorrecta")

        return errors

    async def get_command_suggestions(
        self,
        partial_input: str = "",
        limit: int = 10,
        category_filter: Optional[str] = None
    ) -> List[CommandSuggestion]:
        """
        Obtener sugerencias de comandos basadas en input parcial
        Async pattern para suggestion generation
        """
        return await self._get_command_suggestions(partial_input, limit, category_filter)

    async def _get_command_suggestions(
        self,
        partial_input: str = "",
        limit: int = 10,
        category_filter: Optional[str] = None
    ) -> List[CommandSuggestion]:
        """Implementación interna de sugerencias"""
        suggestions = []
        partial_lower = partial_input.lower()

        for cmd_name, cmd_def in self._command_definitions.items():
            # Filtrar por categoría si se especifica
            if category_filter and cmd_def.category != category_filter:
                continue

            # Calcular relevancia
            relevance = 0.0
            if not partial_input:
                relevance = cmd_def.confidence_base
            elif cmd_name.lower().startswith(partial_lower):
                relevance = 0.9
            elif partial_lower in cmd_name.lower():
                relevance = 0.6
            else:
                continue

            # Crear sugerencia
            suggestion = self._create_command_suggestion(cmd_def)
            suggestion.confidence = relevance
            suggestions.append(suggestion)

        # Ordenar por relevancia y limitar resultados
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:limit]

    def _create_command_suggestion(self, cmd_def: CommandDefinition) -> CommandSuggestion:
        """Crear sugerencia a partir de definición de comando"""
        return CommandSuggestion(
            command=cmd_def.name,
            description=cmd_def.description,
            category=cmd_def.category,
            confidence=cmd_def.confidence_base,
            usage_hint=cmd_def.usage_hint,
            parameters=cmd_def.parameters,
            examples=cmd_def.examples
        )

    async def detect_command_type(self, input_text: str) -> Optional[str]:
        """
        Detectar tipo de comando en el input
        Utilizado para analytics y tracking
        """
        for cmd_name, pattern in self._command_patterns.items():
            if pattern.match(input_text.strip()):
                return cmd_name
        return None

    async def enhance_input_history_entry(self, entry: InputHistoryEntry) -> InputHistoryEntry:
        """
        Enriquecer entrada de historial con detección de comandos
        Async pattern para enrichment pipeline
        """
        # Detectar tipo de comando
        command_type = await self.detect_command_type(entry.text)
        if command_type:
            entry.command_type = command_type
            entry.is_command = True

        # Validar input
        validation_result = await self.validate_input(entry.text)
        entry.validation_status = "valid" if validation_result.is_valid else "invalid"

        return entry

    def get_available_categories(self) -> List[str]:
        """Obtener categorías disponibles de comandos"""
        categories = set()
        for cmd_def in self._command_definitions.values():
            categories.add(cmd_def.category)
        return sorted(list(categories))

    def get_command_count_by_category(self) -> Dict[str, int]:
        """Obtener conteo de comandos por categoría"""
        counts = {}
        for cmd_def in self._command_definitions.values():
            counts[cmd_def.category] = counts.get(cmd_def.category, 0) + 1
        return counts