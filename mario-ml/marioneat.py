""" 2-input XOR example """

from neat import nn, population, statistics, visualize
from emulator import EmulatorExecutor

executor = EmulatorExecutor(1)


def eval_fitness(genomes):
    for g in genomes:
        net = nn.create_feed_forward_phenotype(g)
        executor.submit(net.serial_activate)

    res = executor.get_results()

    for idx, g in enumerate(genomes):
        g.fitness = float(res[idx])


pop = population.Population(r'marioNEAT_config')
#pop.load_checkpoint(r'neat-checkpoint-72')
pop.run(eval_fitness, 300)

print('Number of evaluations: {0}'.format(pop.total_evaluations))

# Display the most fit genome.
winner = pop.statistics.best_genome()
print('\nBest genome:\n{!s}'.format(winner))


# Visualize the winner network and plot/log statistics.
visualize.plot_stats(pop.statistics)
visualize.plot_species(pop.statistics)
#visualize.draw_net(winner, view=True, filename="xor2-all.gv")
#visualize.draw_net(winner, view=True, filename="xor2-enabled.gv", show_disabled=False)
#visualize.draw_net(winner, view=True, filename="xor2-enabled-pruned.gv", show_disabled=False, prune_unused=True)
statistics.save_stats(pop.statistics)
statistics.save_species_count(pop.statistics)
statistics.save_species_fitness(pop.statistics)