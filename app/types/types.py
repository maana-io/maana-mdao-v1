mdao_types = """

type Query {
  problem(driver: DriverAsInput!, independantVariables: [IndependantVariableComponentAsInput!]!, designVariables: [DesignVariableAsInput!]!, explicitComponent: ExplicitComponentAsInput!, constraints: [ConstraintAsInput!]!, objective: ObjectiveAsInput!): [Result]
  multiDisciplineProblem(independantVariables: [IndependantVariableComponentAsInput!]!, group: GroupAsInput, constraints: [ConstraintAsInput!]!, objective: ObjectiveAsInput!): [Result]
  CKGErrors: [String]
}

type Group {
  id: ID!
  name: String
  explicitDisciplines: [ExplicitDiscipline]
}

input GroupAsInput {
  id: ID!
  name: String
  explicitDisciplines: [ExplicitDisciplineAsInput]
}

type ExplicitDiscipline {
  id: ID!
  component: ExplicitComponent
  promotesInputs: [String]
  promotesOutputs: [String]
}

input ExplicitDisciplineAsInput {
  id: ID!
  component: ExplicitComponentAsInput
  promotesInputs: [String]
  promotesOutputs: [String]
}

type Constraint {
  id: ID!
  name: String
  upperBound: Float
  lowerBound: Float
  equation: String
  promotes: [String]
}

input ConstraintAsInput {
  id: ID!
  name: String
  upperBound: Float
  lowerBound: Float
  equation: String
  promotes: [String]
}

scalar Date

scalar DateTime

type DesignVariable {
  id: ID!
  upperBound: Float
  lowerBound: Float
}

input DesignVariableAsInput {
  id: ID!
  upperBound: Float
  lowerBound: Float
}

type Driver {
  id: ID!
  optimizer: String!
}

input DriverAsInput {
  id: ID!
  optimizer: String!
}

type ExecComp {
  id: ID!
}

type ExplicitComponent {
  id: ID!
  name: String
  equation: String!
}

input ExplicitComponentAsInput {
  id: ID!
  name: String
  equation: String!
}

type ImplicitComponent {
  id: ID!
}

type IndependantVariableComponent {
  id: ID!
  value: Float!
}

input IndependantVariableComponentAsInput {
  id: ID!
  value: Float!
}

type Info {
  id: ID!
  name: String!
  description: String
}

scalar JSON


type Objective {
  id: ID!
  equation: String
  promotes: [String]
}

input ObjectiveAsInput {
  id: ID!
  promotes: [String]
  equation: String
}

type Result {
  id: ID!
  value: Float
}

scalar Time



"""