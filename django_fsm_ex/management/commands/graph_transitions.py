# -*- coding: utf-8; mode: django -*-
import graphviz

from django.core.management.base import BaseCommand
from django.utils.encoding import force_text

from django_fsm_ex.fields import FSMFieldMixin
from django_fsm_ex.transition import RETURN_VALUE, GET_STATE

from django.apps import apps


def all_fsm_fields_data(model):
    return [(field, model) for field in model._meta.get_fields()
            if isinstance(field, FSMFieldMixin)]


def node_name(field, state):
    opts = field.model._meta
    return "%s.%s.%s.%s" % (opts.app_label, opts.verbose_name.replace(' ', '_'), field.name, state)

def node_label(field, state):
    if isinstance(state, int):
        return force_text(dict(field.choices).get(state))
    else:
        return state


def generate_dot(fields_data):
    result = graphviz.Digraph()

    for field, model in fields_data:
        sources, targets, edges, any_targets, any_except_targets = set(), set(), set(), set(), set()

        # dump nodes and edges
        for transition in field.get_all_transitions(model):
            if transition.source == '*':
                any_targets.add((transition.target, transition.name))
            elif transition.source == '+':
                any_except_targets.add((transition.target, transition.name))
            else:
                source_name = node_name(field, transition.source)
                if transition.target is not None:
                    if isinstance(transition.target, GET_STATE) or isinstance(transition.target, RETURN_VALUE):
                        if transition.target.allowed_states:
                            for transition_target_index, transition_target in enumerate(transition.target.allowed_states):
                                add_transition(transition.source, transition_target, transition.name,
                                               source_name, field, sources, targets, edges)
                    else:
                        add_transition(transition.source, transition.target, transition.name,
                                       source_name, field, sources, targets, edges)
            if transition.on_error:
                on_error_name = node_name(field, transition.on_error)
                targets.add(
                    (on_error_name, node_label(field, transition.on_error))
                )
                edges.add((source_name, on_error_name, (('style', 'dotted'),)))

        for target, name in any_targets:
            target_name = node_name(field, target)
            targets.add((target_name, node_label(field, target)))
            for source_name, label in sources:
                edges.add((source_name, target_name, (('label', name),)))

        for target, name in any_except_targets:
            target_name = node_name(field, target)
            targets.add((target_name, node_label(field, target)))
            for source_name, label in sources:
                if target_name == source_name:
                    continue
                edges.add((source_name, target_name, (('label', name),)))

        # construct subgraph
        opts = field.model._meta
        subgraph = graphviz.Digraph(
            name="cluster_%s_%s_%s" % (opts.app_label, opts.object_name, field.name),
            graph_attr={'label': "%s.%s.%s" % (opts.app_label, opts.object_name, field.name)})

        final_states = targets - sources
        for name, label in final_states:
            subgraph.node(name, label=label, shape='doublecircle')
        for name, label in (sources | targets) - final_states:
            subgraph.node(name, label=label, shape='circle')
            if field.default:  # Adding initial state notation
                if label == field.default:
                    initial_name = node_name(field, '_initial')
                    subgraph.node(name=initial_name, label='', shape='point')
                    subgraph.edge(initial_name, name)
        for source_name, target_name, attrs in edges:
            subgraph.edge(source_name, target_name, **dict(attrs))

        result.subgraph(subgraph)

    return result


def add_transition(transition_source, transition_target, transition_name, source_name, field, sources, targets, edges):
    target_name = node_name(field, transition_target)
    sources.add((source_name, node_label(field, transition_source)))
    targets.add((target_name, node_label(field, transition_target)))
    edges.add((source_name, target_name, (('label', transition_name),)))


def get_graphviz_layouts():
    try:
        import graphviz

        return graphviz.backend.ENGINES
    except Exception:
        return {'sfdp', 'circo', 'twopi', 'dot', 'neato', 'fdp', 'osage', 'patchwork'}


class Command(BaseCommand):
    requires_system_checks = True


    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o', action='store', dest='outputfile',
            help=('Render output file. Type of output dependent on file extensions. '
                  'Use png or jpg to render graph to image.'))
        parser.add_argument(
            '--layout', '-l', action='store', dest='layout', default='dot',
            help=('Layout to be used by GraphViz for visualization. '
                  'Layouts: %s.' % ' '.join(get_graphviz_layouts())))
        parser.add_argument('args', nargs='*',
                            help=('[appname[.model[.field]]]'))

    help = ("Creates a GraphViz dot file with transitions for selected fields")

    def render_output(self, graph, **options):
        filename, format = options['outputfile'].rsplit('.', 1)

        graph.engine = options['layout']
        graph.format = format
        graph.render(filename)

    def handle(self, *args, **options):
        fields_data = []
        if len(args) != 0:
            for arg in args:
                field_spec = arg.split('.')

                if len(field_spec) == 1:
                    app = apps.get_app(field_spec[0])
                    models = apps.get_models(app)
                    for model in models:
                        fields_data += all_fsm_fields_data(model)
                elif len(field_spec) == 2:
                    model = apps.get_model(field_spec[0], field_spec[1])
                    fields_data += all_fsm_fields_data(model)
                elif len(field_spec) == 3:
                    model = apps.get_model(field_spec[0], field_spec[1])
                    fields_data += all_fsm_fields_data(model)
        else:
            for model in apps.get_models():
                fields_data += all_fsm_fields_data(model)

        dotdata = generate_dot(fields_data)

        if options['outputfile']:
            self.render_output(dotdata, **options)
        else:
            print(dotdata)
